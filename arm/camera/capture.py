#!/usr/bin/env python3
"""
Webcam frame capture with a rolling buffer.

Frames are whatever the source returns: a numpy image from OpenCV, or raw JPEG bytes from the
fake source used in tests. ``encode_jpeg`` and ``crop`` handle both so the daemon logic does not
care which it has. OpenCV is imported lazily so nothing else in ARM depends on it.
"""
import collections
import glob
import logging
import os
import threading
import time
from typing import Any, Deque, Dict, List, Optional, Tuple

Region = Tuple[int, int, int, int]
"""x, y, width, height in pixels"""


def _cv2():
    import cv2  # pylint: disable=import-outside-toplevel
    return cv2


class CameraSource:
    """A V4L2/UVC webcam read through OpenCV."""

    def __init__(self, device: str, width: int = 0, height: int = 0, logger=logging):
        self.device = device
        self.width = width
        self.height = height
        self._cap = None
        self._logger = logger

    def _device_index(self):
        # cv2.VideoCapture accepts an int index or a device path
        base = os.path.basename(str(self.device))
        if base.startswith("video") and base[5:].isdigit():
            return int(base[5:])
        return self.device

    def open(self) -> bool:
        cv2 = _cv2()
        self.release()
        cap = cv2.VideoCapture(self._device_index())
        if not cap.isOpened():
            cap.release()
            self._logger.warning(f"Could not open camera {self.device}")
            return False
        if self.width and self.height:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._cap = cap
        self._logger.info(f"Camera {self.device} opened "
                          f"({int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))})")
        return True

    def read(self) -> Optional[Any]:
        if self._cap is None:
            return None
        ok, frame = self._cap.read()
        return frame if ok else None

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None


class FakeFrameSource:
    """
    Cycles through image files for running the daemon without a camera.

    With OpenCV installed the files are decoded so cropping works; without it the raw file bytes
    are returned and saved untouched (so they should already be JPEGs).
    """

    def __init__(self, path: str, logger=logging):
        if os.path.isdir(path):
            self.files: List[str] = sorted(
                f for ext in ("*.jpg", "*.jpeg", "*.png")
                for f in glob.glob(os.path.join(path, ext))
            )
        else:
            self.files = [path]
        if not self.files:
            raise FileNotFoundError(f"No images found at {path}")
        self._index = 0
        self._logger = logger
        try:
            self._cv2 = _cv2()
        except ImportError:
            self._cv2 = None
            logger.info("OpenCV not installed, fake frames are passed through as raw bytes")

    def open(self) -> bool:
        return True

    def read(self) -> Optional[Any]:
        path = self.files[self._index % len(self.files)]
        self._index += 1
        if self._cv2 is not None:
            frame = self._cv2.imread(path)
            if frame is not None:
                return frame
        with open(path, "rb") as handle:
            return handle.read()

    def release(self) -> None:
        pass


class FrameBuffer:
    """
    Reads frames from a source on a background thread and keeps the last ``buffer_seconds``.

    ``frame_at(ts)`` returns the frame captured closest to a ``time.monotonic()`` timestamp, so
    the daemon can reach back to the moment before a tray started closing.
    """

    def __init__(self, source, fps: float = 5.0, buffer_seconds: float = 4.0, logger=logging):
        self.source = source
        self.interval = 1.0 / max(float(fps), 0.5)
        self.buffer_seconds = max(float(buffer_seconds), self.interval)
        self._frames: Deque[Tuple[float, Any]] = collections.deque()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._logger = logger
        self.frames_read = 0
        self.camera_open = False
        """True while the source is delivering frames (updated by the capture thread)."""

    def start(self) -> None:
        """Start the capture thread, or restart it after it died (see ``_run``)."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="arm-camera-capture", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)
            self._thread = None
        self.source.release()
        self.camera_open = False
        with self._lock:
            self._frames.clear()

    @property
    def running(self) -> bool:
        """True while the capture thread is alive."""
        return self._thread is not None and self._thread.is_alive()

    def _run(self) -> None:
        """
        Thread body. Any exception from the source (a missing cv2, a V4L2 error) is logged once
        and ends the thread with ``camera_open`` False; the daemon restarts it with a backoff.
        """
        try:
            self._capture_loop()
        except Exception as error:  # pylint: disable=broad-except
            self._logger.error(f"Camera capture stopped: {error}", exc_info=True)
        finally:
            self.camera_open = False
            try:
                self.source.release()
            except Exception:  # pylint: disable=broad-except
                pass

    def _capture_loop(self) -> None:
        backoff = 1.0
        opened = self.source.open()
        while not self._stop.is_set():
            self.camera_open = opened
            if not opened:
                self._logger.warning(f"Camera unavailable, retrying in {backoff:.0f}s")
                if self._stop.wait(backoff):
                    break
                backoff = min(backoff * 2, 60.0)
                opened = self.source.open()
                continue
            started = time.monotonic()
            frame = self.source.read()
            if frame is None:
                self._logger.warning("Camera read failed, reopening")
                opened = False
                continue
            backoff = 1.0
            self._append(time.monotonic(), frame)
            elapsed = time.monotonic() - started
            self._stop.wait(max(self.interval - elapsed, 0.0))

    def _append(self, timestamp: float, frame: Any) -> None:
        with self._lock:
            self._frames.append((timestamp, frame))
            self.frames_read += 1
            cutoff = timestamp - self.buffer_seconds
            while self._frames and self._frames[0][0] < cutoff:
                self._frames.popleft()

    def __len__(self) -> int:
        with self._lock:
            return len(self._frames)

    def latest(self) -> Optional[Tuple[float, Any]]:
        """The newest ``(timestamp, frame)`` pair, or ``None`` when the buffer is empty."""
        with self._lock:
            return self._frames[-1] if self._frames else None

    def frame_at(self, timestamp: float) -> Optional[Any]:
        """The buffered frame captured closest to ``timestamp``, or ``None`` when the buffer is empty."""
        with self._lock:
            if not self._frames:
                return None
            return min(self._frames, key=lambda item: abs(item[0] - timestamp))[1]

    def wait_for_frame(self, timeout: float = 5.0) -> bool:
        """Block until at least one frame has been captured. Returns False on timeout."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if len(self):
                return True
            time.sleep(0.05)
        return len(self) > 0


def crop(frame: Any, region: Optional[Region]) -> Any:
    """Crop a numpy frame to ``region``; raw byte frames and empty regions pass through."""
    if region is None or isinstance(frame, (bytes, bytearray)):
        return frame
    x, y, width, height = region
    frame_height, frame_width = frame.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(frame_width, x + width), min(frame_height, y + height)
    if x1 <= x0 or y1 <= y0:
        return frame
    return frame[y0:y1, x0:x1]


def frame_size(frame: Any) -> Optional[Tuple[int, int]]:
    """``(width, height)`` of a numpy frame; ``None`` for raw byte frames or when there is no frame."""
    shape = getattr(frame, "shape", None)
    if not shape or len(shape) < 2:
        return None
    return int(shape[1]), int(shape[0])


def draw_regions(frame: Any, regions: Dict[str, Region]) -> Any:
    """
    Return a copy of a numpy frame with each crop region drawn as a labelled rectangle.

    Raw byte frames (no OpenCV) and empty region maps pass through untouched.
    """
    if not regions or isinstance(frame, (bytes, bytearray)) or getattr(frame, "shape", None) is None:
        return frame
    try:
        cv2 = _cv2()
    except ImportError:
        return frame
    canvas = frame.copy()
    for name, (x, y, width, height) in sorted(regions.items()):
        cv2.rectangle(canvas, (int(x), int(y)), (int(x + width), int(y + height)), (0, 255, 0), 2)
        label_y = int(y) - 8 if y > 20 else int(y + height) + 20
        cv2.putText(canvas, str(name), (int(x) + 4, label_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2,
                    cv2.LINE_AA)
    return canvas


def encode_jpeg(frame: Any, quality: int = 85) -> bytes:
    """JPEG-encode a numpy frame; raw byte frames are returned as they are."""
    if isinstance(frame, (bytes, bytearray)):
        return bytes(frame)
    cv2 = _cv2()
    ok, data = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)])
    if not ok:
        raise RuntimeError("cv2.imencode failed")
    return data.tobytes()
