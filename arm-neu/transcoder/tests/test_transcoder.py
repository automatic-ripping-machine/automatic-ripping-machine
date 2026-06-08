"""
Tests for transcoder.py - TranscodeWorker unit tests.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from models import TranscodeJob
from transcoder import log_filename


def test_log_filename_format():
    """log_filename() returns JOB_{id}_Transcode.log"""
    assert log_filename(42) == "JOB_42_Transcode.log"
    assert log_filename(1) == "JOB_1_Transcode.log"


# Default GPU support dict for mocking
def _gpu_support_all():
    return {
        "handbrake_nvenc": True,
        "ffmpeg_nvenc_h265": True,
        "ffmpeg_nvenc_h264": True,
        "ffmpeg_vaapi_h265": True,
        "ffmpeg_vaapi_h264": True,
        "ffmpeg_amf_h265": True,
        "ffmpeg_amf_h264": True,
        "ffmpeg_qsv_h265": True,
        "ffmpeg_qsv_h264": True,
        "vaapi_device": True,
    }


def _gpu_support_none():
    return {k: False for k in _gpu_support_all()}


def _mock_scheme(video_encoder="x265"):
    """Build a mock active_scheme with the given default video_encoder."""
    from presets import Preset, Scheme, Encoder

    preset = Preset(
        slug="test_preset", name="Test Preset", scheme="test",
        shared={
            "video_encoder": video_encoder,
            "audio_encoder": "copy",
            "subtitle_mode": "all",
        },
        tiers={
            "dvd": {"handbrake_preset": "Test 720p", "video_quality": 22, "handbrake_extra_args": ["--width", "1280"]},
            "bluray": {"handbrake_preset": "Test 1080p", "video_quality": 22},
            "uhd": {"handbrake_preset": "Test 2160p 4K", "video_quality": 22},
        },
    )
    scheme = Scheme(
        slug="test", name="Test",
        supported_encoders=[Encoder(slug=video_encoder, name=video_encoder)],
        supported_audio_encoders=["copy", "aac"],
        supported_subtitle_modes=["all", "first", "none"],
        built_in_presets=[preset],
    )
    return scheme


# --- check_gpu_support ---


class TestCheckGpuSupport:
    """Tests for check_gpu_support function."""

    def _hb_help(self, *, nvenc=False, qsv=False):
        """Build a mock HandBrakeCLI --help result."""
        result = MagicMock()
        bits = []
        if nvenc:
            bits.append("nvenc")
        if qsv:
            bits.append("qsv")
        result.stdout = " ".join(bits)
        result.stderr = ""
        return result

    def test_all_available(self):
        """Should detect all GPU encoders when hardware probes succeed."""
        def mock_run(cmd, **kwargs):
            if cmd[0] == "HandBrakeCLI":
                return self._hb_help(nvenc=True, qsv=True)
            return MagicMock()  # any ffmpeg subprocess call

        with patch("transcoder.subprocess.run", side_effect=mock_run), \
             patch("transcoder._ffmpeg_has_encoder", return_value=True), \
             patch("transcoder._ffmpeg_encoder_works", return_value=True), \
             patch("transcoder.os.path.exists", return_value=True):
            from transcoder import check_gpu_support
            support = check_gpu_support()
            assert support["handbrake_nvenc"] is True
            assert support["handbrake_qsv"] is True
            assert support["ffmpeg_nvenc_h265"] is True
            assert support["ffmpeg_nvenc_h264"] is True
            assert support["ffmpeg_vaapi_h265"] is True
            assert support["ffmpeg_vaapi_h264"] is True
            assert support["ffmpeg_amf_h265"] is True
            assert support["ffmpeg_amf_h264"] is True
            assert support["ffmpeg_qsv_h265"] is True
            assert support["ffmpeg_qsv_h264"] is True
            assert support["vaapi_device"] is True

    def test_nothing_available(self):
        """Should handle no GPU support (probes fail, no device)."""
        def mock_run(cmd, **kwargs):
            raise FileNotFoundError("not found")

        with patch("transcoder.subprocess.run", side_effect=mock_run), \
             patch("transcoder._ffmpeg_has_encoder", return_value=False), \
             patch("transcoder._ffmpeg_encoder_works", return_value=False), \
             patch("transcoder.os.path.exists", return_value=False):
            from transcoder import check_gpu_support
            support = check_gpu_support()
            assert support["handbrake_nvenc"] is False
            assert all(
                support[k] is False
                for k in support
                if k.startswith("ffmpeg_")
            )
            assert support["vaapi_device"] is False

    def test_ffmpeg_encoder_compiled_but_hardware_missing(self):
        """KEY REGRESSION: compiled-in ffmpeg encoder but no hardware must return false."""
        def mock_run(cmd, **kwargs):
            if cmd[0] == "HandBrakeCLI":
                raise FileNotFoundError()
            return MagicMock()

        # has_encoder returns True (compiled in); encoder_works returns False (no hw)
        with patch("transcoder.subprocess.run", side_effect=mock_run), \
             patch("transcoder._ffmpeg_has_encoder", return_value=True), \
             patch("transcoder._ffmpeg_encoder_works", return_value=False), \
             patch("transcoder.os.path.exists", return_value=False):
            from transcoder import check_gpu_support
            support = check_gpu_support()
            assert support["ffmpeg_nvenc_h265"] is False
            assert support["ffmpeg_nvenc_h264"] is False
            assert support["ffmpeg_amf_h265"] is False
            assert support["ffmpeg_amf_h264"] is False

    def test_ffmpeg_only_nvenc(self):
        """Should detect FFmpeg NVENC when HandBrake missing and hardware works."""
        def mock_run(cmd, **kwargs):
            if cmd[0] == "HandBrakeCLI":
                raise FileNotFoundError()
            return MagicMock()

        def has_encoder(enc):
            return enc in ("hevc_nvenc", "h264_nvenc")

        def encoder_works(enc, hwaccel=None):
            return enc in ("hevc_nvenc", "h264_nvenc")

        with patch("transcoder.subprocess.run", side_effect=mock_run), \
             patch("transcoder._ffmpeg_has_encoder", side_effect=has_encoder), \
             patch("transcoder._ffmpeg_encoder_works", side_effect=encoder_works), \
             patch("transcoder.os.path.exists", return_value=False):
            from transcoder import check_gpu_support
            support = check_gpu_support()
            assert support["handbrake_nvenc"] is False
            assert support["ffmpeg_nvenc_h265"] is True
            assert support["ffmpeg_nvenc_h264"] is True
            assert support["ffmpeg_vaapi_h265"] is False
            assert support["ffmpeg_vaapi_h264"] is False

    def test_vaapi_only(self):
        """Should detect VAAPI encoders when device present and hardware works."""
        def mock_run(cmd, **kwargs):
            if cmd[0] == "HandBrakeCLI":
                raise FileNotFoundError()
            return MagicMock()

        def has_encoder(enc):
            return enc in ("hevc_vaapi", "h264_vaapi")

        def encoder_works(enc, hwaccel=None):
            return enc in ("hevc_vaapi", "h264_vaapi")

        with patch("transcoder.subprocess.run", side_effect=mock_run), \
             patch("transcoder._ffmpeg_has_encoder", side_effect=has_encoder), \
             patch("transcoder._ffmpeg_encoder_works", side_effect=encoder_works), \
             patch("transcoder.os.path.exists", return_value=True):
            from transcoder import check_gpu_support
            support = check_gpu_support()
            assert support["handbrake_nvenc"] is False
            assert support["ffmpeg_nvenc_h265"] is False
            assert support["ffmpeg_vaapi_h265"] is True
            assert support["ffmpeg_vaapi_h264"] is True
            assert support["vaapi_device"] is True

    def test_qsv_only(self):
        """Should detect QSV encoders when device present and hardware works."""
        def mock_run(cmd, **kwargs):
            if cmd[0] == "HandBrakeCLI":
                raise FileNotFoundError()
            return MagicMock()

        def has_encoder(enc):
            return enc in ("hevc_qsv", "h264_qsv")

        def encoder_works(enc, hwaccel=None):
            return enc in ("hevc_qsv", "h264_qsv")

        with patch("transcoder.subprocess.run", side_effect=mock_run), \
             patch("transcoder._ffmpeg_has_encoder", side_effect=has_encoder), \
             patch("transcoder._ffmpeg_encoder_works", side_effect=encoder_works), \
             patch("transcoder.os.path.exists", return_value=True):
            from transcoder import check_gpu_support
            support = check_gpu_support()
            assert support["handbrake_nvenc"] is False
            assert support["ffmpeg_nvenc_h265"] is False
            assert support["ffmpeg_qsv_h265"] is True
            assert support["ffmpeg_qsv_h264"] is True
            assert support["vaapi_device"] is True

    def test_handbrake_nvenc_in_stderr(self):
        """HandBrake may report NVENC in stderr."""
        def mock_run(cmd, **kwargs):
            result = MagicMock()
            if cmd[0] == "HandBrakeCLI":
                result.stdout = ""
                result.stderr = "NVENC encoder available"
            else:
                result.stdout = ""
                result.stderr = ""
            return result

        with patch("transcoder.subprocess.run", side_effect=mock_run), \
             patch("transcoder._ffmpeg_has_encoder", return_value=False), \
             patch("transcoder._ffmpeg_encoder_works", return_value=False), \
             patch("transcoder.os.path.exists", return_value=False):
            from transcoder import check_gpu_support
            support = check_gpu_support()
            assert support["handbrake_nvenc"] is True

    def test_vaapi_device_not_found_skips_probe(self):
        """When /dev/dri/renderD128 is missing, VAAPI/QSV probes are skipped entirely."""
        def mock_run(cmd, **kwargs):
            if cmd[0] == "HandBrakeCLI":
                raise FileNotFoundError()
            return MagicMock()

        # Even if encoders would work, skip them when no device
        with patch("transcoder.subprocess.run", side_effect=mock_run), \
             patch("transcoder._ffmpeg_has_encoder", return_value=True), \
             patch("transcoder._ffmpeg_encoder_works", return_value=True), \
             patch("transcoder.os.path.exists", return_value=False):
            from transcoder import check_gpu_support
            support = check_gpu_support()
            assert support["vaapi_device"] is False
            # VAAPI and QSV probes short-circuit when no device
            assert support["ffmpeg_vaapi_h265"] is False
            assert support["ffmpeg_vaapi_h264"] is False
            assert support["ffmpeg_qsv_h265"] is False
            assert support["ffmpeg_qsv_h264"] is False

    def test_backward_compat_alias(self):
        """check_nvenc_support should be an alias for check_gpu_support."""
        from transcoder import check_nvenc_support, check_gpu_support
        assert check_nvenc_support is check_gpu_support


class TestFfmpegEncoderProbeHelpers:
    """Tests for the probe helpers that back check_gpu_support."""

    def test_has_encoder_true(self):
        result = MagicMock()
        result.stdout = "V..... hevc_nvenc          NVIDIA NVENC hevc encoder\n"
        with patch("transcoder.subprocess.run", return_value=result):
            from transcoder import _ffmpeg_has_encoder
            assert _ffmpeg_has_encoder("hevc_nvenc") is True

    def test_has_encoder_false(self):
        result = MagicMock()
        result.stdout = "V..... libx265          H.265 / HEVC (libx265)\n"
        with patch("transcoder.subprocess.run", return_value=result):
            from transcoder import _ffmpeg_has_encoder
            assert _ffmpeg_has_encoder("hevc_nvenc") is False

    def test_has_encoder_ffmpeg_missing(self):
        with patch("transcoder.subprocess.run", side_effect=FileNotFoundError):
            from transcoder import _ffmpeg_has_encoder
            assert _ffmpeg_has_encoder("hevc_nvenc") is False

    def test_encoder_works_success(self):
        result = MagicMock()
        result.returncode = 0
        with patch("transcoder.subprocess.run", return_value=result):
            from transcoder import _ffmpeg_encoder_works
            assert _ffmpeg_encoder_works("libx265") is True

    def test_encoder_works_failure(self):
        """Non-zero exit code (e.g. no device available) returns False."""
        result = MagicMock()
        result.returncode = 1
        with patch("transcoder.subprocess.run", return_value=result):
            from transcoder import _ffmpeg_encoder_works
            assert _ffmpeg_encoder_works("hevc_nvenc") is False

    def test_encoder_works_timeout(self):
        import subprocess as sp
        with patch("transcoder.subprocess.run",
                    side_effect=sp.TimeoutExpired(cmd="ffmpeg", timeout=10)):
            from transcoder import _ffmpeg_encoder_works
            assert _ffmpeg_encoder_works("hevc_nvenc") is False

    def test_encoder_works_passes_hwaccel(self):
        """hwaccel arg should appear in ffmpeg command when provided."""
        captured = {}
        def capture(cmd, **kwargs):
            captured["cmd"] = cmd
            r = MagicMock()
            r.returncode = 0
            return r
        with patch("transcoder.subprocess.run", side_effect=capture):
            from transcoder import _ffmpeg_encoder_works
            _ffmpeg_encoder_works("hevc_vaapi", hwaccel="vaapi")
            assert "-hwaccel" in captured["cmd"]
            assert "vaapi" in captured["cmd"]


# --- Encoder family detection ---


class TestEncoderFamilyDetection:
    """Tests for _detect_encoder_family and _select_backend."""

    def _make_worker(self, gpu_support=None, video_encoder="nvenc_h265"):
        if gpu_support is None:
            gpu_support = _gpu_support_all()
        scheme = _mock_scheme(video_encoder)
        with patch("transcoder.check_gpu_support", return_value=gpu_support), \
             patch("main.active_scheme", scheme):
            from transcoder import TranscodeWorker
            return TranscodeWorker()

    def test_nvenc_family(self):
        worker = self._make_worker(video_encoder="nvenc_h265")
        assert worker._encoder_family == "nvenc"

    def test_vaapi_family(self):
        worker = self._make_worker(video_encoder="vaapi_h265")
        assert worker._encoder_family == "vaapi"

    def test_amf_family(self):
        worker = self._make_worker(video_encoder="amf_h265")
        assert worker._encoder_family == "amf"

    def test_qsv_family(self):
        worker = self._make_worker(video_encoder="qsv_h265")
        assert worker._encoder_family == "qsv"

    def test_software_family(self):
        worker = self._make_worker(video_encoder="x265")
        assert worker._encoder_family == "software"

    def test_nvenc_uses_handbrake_when_available(self):
        worker = self._make_worker(video_encoder="nvenc_h265")
        assert worker._encoder_backend == "handbrake"

    def test_nvenc_falls_back_to_ffmpeg(self):
        support = _gpu_support_none()
        support["ffmpeg_nvenc_h265"] = True
        worker = self._make_worker(gpu_support=support, video_encoder="nvenc_h265")
        assert worker._encoder_backend == "ffmpeg"

    def test_vaapi_always_uses_ffmpeg(self):
        worker = self._make_worker(video_encoder="vaapi_h265")
        assert worker._encoder_backend == "ffmpeg"

    def test_amf_always_uses_ffmpeg(self):
        worker = self._make_worker(video_encoder="amf_h265")
        assert worker._encoder_backend == "ffmpeg"

    def test_qsv_uses_ffmpeg(self):
        worker = self._make_worker(video_encoder="qsv_h265")
        assert worker._encoder_backend == "ffmpeg"

    def test_software_uses_ffmpeg(self):
        worker = self._make_worker(video_encoder="x264")
        assert worker._encoder_backend == "ffmpeg"


# --- FFmpeg command building ---


class TestBuildFfmpegCommand:
    """Tests for _build_ffmpeg_command with different encoder families."""

    def _make_worker(self, video_encoder="nvenc_h265"):
        scheme = _mock_scheme(video_encoder)
        with patch("transcoder.check_gpu_support", return_value=_gpu_support_all()), \
             patch("main.active_scheme", scheme):
            from transcoder import TranscodeWorker
            return TranscodeWorker()

    def _effective(self, video_encoder="nvenc_h265", video_quality=22,
                   audio_encoder="copy", subtitle_mode="all"):
        """Build an effective settings dict for _build_ffmpeg_command."""
        return {
            "video_encoder": video_encoder,
            "video_quality": video_quality,
            "audio_encoder": audio_encoder,
            "subtitle_mode": subtitle_mode,
        }

    def test_nvenc_h265_command(self):
        worker = self._make_worker("nvenc_h265")
        cmd = worker._build_ffmpeg_command(
            Path("/in.mkv"), Path("/out.mkv"),
            self._effective("nvenc_h265"),
        )
        assert "-hwaccel" in cmd
        assert "cuda" in cmd
        assert "hevc_nvenc" in cmd
        assert "-cq" in cmd
        assert "-map" in cmd
        assert "0:v:0" in cmd
        assert "0:a?" in cmd

    def test_nvenc_h264_command(self):
        worker = self._make_worker("nvenc_h264")
        cmd = worker._build_ffmpeg_command(
            Path("/in.mkv"), Path("/out.mkv"),
            self._effective("nvenc_h264"),
        )
        assert "h264_nvenc" in cmd

    def test_vaapi_h265_command(self):
        worker = self._make_worker("vaapi_h265")
        cmd = worker._build_ffmpeg_command(
            Path("/in.mkv"), Path("/out.mkv"),
            self._effective("vaapi_h265"),
        )
        assert "-hwaccel" in cmd
        assert "vaapi" in cmd
        assert "hevc_vaapi" in cmd
        assert "-rc_mode" in cmd
        assert "CQP" in cmd
        assert "-qp" in cmd

    def test_vaapi_h264_command(self):
        worker = self._make_worker("vaapi_h264")
        cmd = worker._build_ffmpeg_command(
            Path("/in.mkv"), Path("/out.mkv"),
            self._effective("vaapi_h264"),
        )
        assert "h264_vaapi" in cmd

    def test_amf_h265_command(self):
        worker = self._make_worker("amf_h265")
        cmd = worker._build_ffmpeg_command(
            Path("/in.mkv"), Path("/out.mkv"),
            self._effective("amf_h265"),
        )
        assert "hevc_amf" in cmd
        assert "-rc" in cmd
        assert "cqp" in cmd
        assert "-qp_i" in cmd

    def test_qsv_h265_command(self):
        worker = self._make_worker("qsv_h265")
        cmd = worker._build_ffmpeg_command(
            Path("/in.mkv"), Path("/out.mkv"),
            self._effective("qsv_h265"),
        )
        assert "-hwaccel" in cmd
        assert "qsv" in cmd
        assert "hevc_qsv" in cmd
        assert "-global_quality" in cmd

    def test_qsv_h264_command(self):
        worker = self._make_worker("qsv_h264")
        cmd = worker._build_ffmpeg_command(
            Path("/in.mkv"), Path("/out.mkv"),
            self._effective("qsv_h264"),
        )
        assert "h264_qsv" in cmd
        assert "-global_quality" in cmd

    def test_software_x265_command(self):
        worker = self._make_worker("x265")
        cmd = worker._build_ffmpeg_command(
            Path("/in.mkv"), Path("/out.mkv"),
            self._effective("x265"),
        )
        assert "libx265" in cmd
        assert "-crf" in cmd
        assert "-hwaccel" not in cmd

    def test_software_x264_command(self):
        worker = self._make_worker("x264")
        cmd = worker._build_ffmpeg_command(
            Path("/in.mkv"), Path("/out.mkv"),
            self._effective("x264"),
        )
        assert "libx264" in cmd
        assert "-crf" in cmd
        assert "-hwaccel" not in cmd

    def test_audio_copy(self):
        worker = self._make_worker("nvenc_h265")
        cmd = worker._build_ffmpeg_command(
            Path("/in.mkv"), Path("/out.mkv"),
            self._effective("nvenc_h265"),
        )
        idx = cmd.index("-c:a")
        assert cmd[idx + 1] == "copy"

    def test_subtitle_all(self):
        worker = self._make_worker("nvenc_h265")
        cmd = worker._build_ffmpeg_command(
            Path("/in.mkv"), Path("/out.mkv"),
            self._effective("nvenc_h265", subtitle_mode="all"),
        )
        assert "0:s?" in cmd
        idx = cmd.index("-c:s")
        assert cmd[idx + 1] == "copy"

    def test_subtitle_none(self):
        worker = self._make_worker("nvenc_h265")
        cmd = worker._build_ffmpeg_command(
            Path("/in.mkv"), Path("/out.mkv"),
            self._effective("nvenc_h265", subtitle_mode="none"),
        )
        assert "0:s?" not in cmd
        assert "0:s:0?" not in cmd
        assert "-c:s" not in cmd

    def test_subtitle_first(self):
        worker = self._make_worker("nvenc_h265")
        cmd = worker._build_ffmpeg_command(
            Path("/in.mkv"), Path("/out.mkv"),
            self._effective("nvenc_h265", subtitle_mode="first"),
        )
        assert "0:s:0?" in cmd
        idx = cmd.index("-c:s")
        assert cmd[idx + 1] == "copy"

    def test_vaapi_includes_device_path(self):
        worker = self._make_worker("vaapi_h265")
        with patch.dict("os.environ", {"VAAPI_DEVICE": "/dev/dri/renderD128"}):
            cmd = worker._build_ffmpeg_command(
                Path("/in.mkv"), Path("/out.mkv"),
                self._effective("vaapi_h265"),
            )
        assert "-hwaccel_device" in cmd
        device_idx = cmd.index("-hwaccel_device")
        assert cmd[device_idx + 1] == "/dev/dri/renderD128"

    def test_nvenc_480p_upscale(self):
        """NVENC FFmpeg should use scale_cuda for DVD upscale."""
        worker = self._make_worker("nvenc_h265")
        cmd = worker._build_ffmpeg_command(
            Path("/in.mkv"), Path("/out.mkv"),
            self._effective("nvenc_h265"),
            resolution=(720, 480),
        )
        assert "-vf" in cmd
        vf_idx = cmd.index("-vf")
        assert "scale_cuda=1280:-2" in cmd[vf_idx + 1]

    def test_vaapi_480p_upscale(self):
        """VAAPI FFmpeg should use scale_vaapi for DVD upscale."""
        worker = self._make_worker("vaapi_h265")
        cmd = worker._build_ffmpeg_command(
            Path("/in.mkv"), Path("/out.mkv"),
            self._effective("vaapi_h265"),
            resolution=(720, 480),
        )
        assert "-vf" in cmd
        vf_idx = cmd.index("-vf")
        assert "scale_vaapi=w=1280:h=-2" in cmd[vf_idx + 1]

    def test_qsv_480p_upscale(self):
        """QSV FFmpeg should use vpp_qsv for DVD upscale."""
        worker = self._make_worker("qsv_h265")
        cmd = worker._build_ffmpeg_command(
            Path("/in.mkv"), Path("/out.mkv"),
            self._effective("qsv_h265"),
            resolution=(720, 480),
        )
        assert "-vf" in cmd
        vf_idx = cmd.index("-vf")
        assert "vpp_qsv=w=1280:h=-2" in cmd[vf_idx + 1]

    def test_amf_480p_upscale(self):
        """AMF FFmpeg should use software scale for DVD upscale."""
        worker = self._make_worker("amf_h265")
        cmd = worker._build_ffmpeg_command(
            Path("/in.mkv"), Path("/out.mkv"),
            self._effective("amf_h265"),
            resolution=(720, 480),
        )
        assert "-vf" in cmd
        vf_idx = cmd.index("-vf")
        assert "scale=1280:-2" in cmd[vf_idx + 1]

    def test_software_480p_upscale(self):
        """Software FFmpeg should use software scale for DVD upscale."""
        worker = self._make_worker("x265")
        cmd = worker._build_ffmpeg_command(
            Path("/in.mkv"), Path("/out.mkv"),
            self._effective("x265"),
            resolution=(720, 480),
        )
        assert "-vf" in cmd
        vf_idx = cmd.index("-vf")
        assert "scale=1280:-2" in cmd[vf_idx + 1]

    def test_1080p_no_scale(self):
        """1080p source should not add any scale filter."""
        worker = self._make_worker("nvenc_h265")
        cmd = worker._build_ffmpeg_command(
            Path("/in.mkv"), Path("/out.mkv"),
            self._effective("nvenc_h265"),
            resolution=(1920, 1080),
        )
        assert "-vf" not in cmd

    def test_4k_no_scale(self):
        """4K source should not add any scale filter."""
        worker = self._make_worker("nvenc_h265")
        cmd = worker._build_ffmpeg_command(
            Path("/in.mkv"), Path("/out.mkv"),
            self._effective("nvenc_h265"),
            resolution=(3840, 2160),
        )
        assert "-vf" not in cmd

    def test_no_resolution_no_scale(self):
        """No resolution info should not add any scale filter."""
        worker = self._make_worker("nvenc_h265")
        cmd = worker._build_ffmpeg_command(
            Path("/in.mkv"), Path("/out.mkv"),
            self._effective("nvenc_h265"),
            resolution=None,
        )
        assert "-vf" not in cmd

    def test_576p_pal_dvd_upscale(self):
        """PAL DVD (576p) should also be upscaled."""
        worker = self._make_worker("nvenc_h265")
        cmd = worker._build_ffmpeg_command(
            Path("/in.mkv"), Path("/out.mkv"),
            self._effective("nvenc_h265"),
            resolution=(720, 576),
        )
        assert "-vf" in cmd
        vf_idx = cmd.index("-vf")
        assert "scale_cuda=1280:-2" in cmd[vf_idx + 1]


# _resolve_source_path was removed in v18.0.0 - ARM now sends the
# input_path directly via the webhook, joined to settings.raw_path
# without further resolution.


# --- TranscodeWorker._discover_source_files ---


class TestDiscoverSourceFiles:
    """Tests for _discover_source_files method."""

    def _make_worker(self):
        scheme = _mock_scheme("x265")
        with patch("transcoder.check_gpu_support", return_value=_gpu_support_all()), \
             patch("main.active_scheme", scheme):
            from transcoder import TranscodeWorker
            return TranscodeWorker()

    def test_finds_mkv_files(self, sample_mkv_dir):
        worker = self._make_worker()
        files = worker._discover_source_files(str(sample_mkv_dir["dir"]))
        assert len(files) == 2
        names = {f.name for f in files}
        assert "title_main.mkv" in names
        assert "title_extra.mkv" in names

    def test_sorted_by_size(self, sample_mkv_dir):
        worker = self._make_worker()
        files = worker._discover_source_files(str(sample_mkv_dir["dir"]))
        assert files[0].name == "title_main.mkv"

    def test_single_file(self, tmp_path):
        mkv = tmp_path / "movie.mkv"
        mkv.write_bytes(b"\x00" * 100)
        worker = self._make_worker()
        files = worker._discover_source_files(str(mkv))
        assert len(files) == 1
        assert files[0].name == "movie.mkv"

    def test_no_mkv_files(self, tmp_path):
        (tmp_path / "readme.txt").write_text("not a video")
        worker = self._make_worker()
        files = worker._discover_source_files(str(tmp_path))
        assert len(files) == 0

    def test_non_mkv_single_file(self, tmp_path):
        txt = tmp_path / "readme.txt"
        txt.write_text("not a video")
        worker = self._make_worker()
        files = worker._discover_source_files(str(txt))
        assert len(files) == 0

    def test_ignores_non_mkv_in_dir(self, tmp_path):
        (tmp_path / "movie.mkv").write_bytes(b"\x00" * 100)
        (tmp_path / "cover.jpg").write_bytes(b"\x00" * 50)
        (tmp_path / "subs.srt").write_text("subtitle")
        worker = self._make_worker()
        files = worker._discover_source_files(str(tmp_path))
        assert len(files) == 1
        assert files[0].suffix == ".mkv"


# --- TranscodeWorker._discover_audio_files ---


class TestDiscoverAudioFiles:
    """Tests for _discover_audio_files method."""

    def _make_worker(self):
        scheme = _mock_scheme("x265")
        with patch("transcoder.check_gpu_support", return_value=_gpu_support_all()), \
             patch("main.active_scheme", scheme):
            from transcoder import TranscodeWorker
            return TranscodeWorker()

    def test_finds_flac_files(self, tmp_path):
        (tmp_path / "track01.flac").write_bytes(b"\x00" * 100)
        (tmp_path / "track02.flac").write_bytes(b"\x00" * 200)
        worker = self._make_worker()
        files = worker._discover_audio_files(str(tmp_path))
        assert len(files) == 2
        names = {f.name for f in files}
        assert "track01.flac" in names
        assert "track02.flac" in names

    def test_finds_mixed_audio_formats(self, tmp_path):
        (tmp_path / "track.flac").write_bytes(b"\x00" * 100)
        (tmp_path / "track.mp3").write_bytes(b"\x00" * 100)
        (tmp_path / "track.ogg").write_bytes(b"\x00" * 100)
        (tmp_path / "track.wav").write_bytes(b"\x00" * 100)
        (tmp_path / "track.m4a").write_bytes(b"\x00" * 100)
        worker = self._make_worker()
        files = worker._discover_audio_files(str(tmp_path))
        assert len(files) == 5

    def test_returns_empty_for_mkv_only(self, tmp_path):
        (tmp_path / "movie.mkv").write_bytes(b"\x00" * 100)
        worker = self._make_worker()
        files = worker._discover_audio_files(str(tmp_path))
        assert len(files) == 0

    def test_returns_empty_for_empty_dir(self, tmp_path):
        worker = self._make_worker()
        files = worker._discover_audio_files(str(tmp_path))
        assert len(files) == 0

    def test_ignores_non_audio_files(self, tmp_path):
        (tmp_path / "track.flac").write_bytes(b"\x00" * 100)
        (tmp_path / "cover.jpg").write_bytes(b"\x00" * 50)
        (tmp_path / "playlist.m3u").write_text("list")
        worker = self._make_worker()
        files = worker._discover_audio_files(str(tmp_path))
        assert len(files) == 1
        assert files[0].suffix == ".flac"

    def test_single_audio_file(self, tmp_path):
        flac = tmp_path / "track.flac"
        flac.write_bytes(b"\x00" * 100)
        worker = self._make_worker()
        files = worker._discover_audio_files(str(flac))
        assert len(files) == 1
        assert files[0].name == "track.flac"

    def test_single_non_audio_file(self, tmp_path):
        txt = tmp_path / "readme.txt"
        txt.write_text("not audio")
        worker = self._make_worker()
        files = worker._discover_audio_files(str(txt))
        assert len(files) == 0

    def test_sorted_by_name(self, tmp_path):
        (tmp_path / "track03.flac").write_bytes(b"\x00" * 100)
        (tmp_path / "track01.flac").write_bytes(b"\x00" * 100)
        (tmp_path / "track02.flac").write_bytes(b"\x00" * 100)
        worker = self._make_worker()
        files = worker._discover_audio_files(str(tmp_path))
        assert [f.name for f in files] == ["track01.flac", "track02.flac", "track03.flac"]


# --- TranscodeWorker._detect_video_type ---


class TestDetectVideoType:
    """Tests for _detect_video_type method."""

    def _make_worker(self):
        scheme = _mock_scheme("x265")
        with patch("transcoder.check_gpu_support", return_value=_gpu_support_all()), \
             patch("main.active_scheme", scheme):
            from transcoder import TranscodeWorker
            return TranscodeWorker()

    def test_movie_title_with_year(self):
        worker = self._make_worker()
        assert worker._detect_video_type("The Matrix (1999)", "/data/raw/The Matrix (1999)") == "movie"

    def test_movie_plain_title(self):
        worker = self._make_worker()
        assert worker._detect_video_type("Inception", "/data/raw/Inception") == "movie"

    def test_tv_season_and_episode(self):
        worker = self._make_worker()
        assert worker._detect_video_type("Breaking Bad S01E01", "/data/raw/Breaking Bad S01E01") == "tv"

    def test_tv_season_only(self):
        worker = self._make_worker()
        assert worker._detect_video_type("The Office S02", "/data/raw/The Office S02") == "tv"

    def test_tv_detected_from_source_path(self):
        worker = self._make_worker()
        assert worker._detect_video_type("ARM notification", "/data/raw/Seinfeld S05E03") == "tv"

    def test_tv_case_insensitive(self):
        worker = self._make_worker()
        assert worker._detect_video_type("show s01e01", "/data/raw/show") == "tv"

    def test_tv_underscore_separator(self):
        worker = self._make_worker()
        assert worker._detect_video_type("Show_S03E12", "/data/raw/Show_S03E12") == "tv"

    def test_movie_with_s_in_title(self):
        """Title containing 'S' followed by non-season digits should be movie."""
        worker = self._make_worker()
        assert worker._detect_video_type("Spider-Man", "/data/raw/Spider-Man") == "movie"


# --- TranscodeWorker._determine_output_path ---


class TestDetermineOutputPath:
    """Tests for _determine_output_path method."""

    def _make_worker(self):
        scheme = _mock_scheme("x265")
        with patch("transcoder.check_gpu_support", return_value=_gpu_support_all()), \
             patch("main.active_scheme", scheme):
            from transcoder import TranscodeWorker
            return TranscodeWorker()

    def test_normal_title(self):
        worker = self._make_worker()
        result = worker._determine_output_path("The Matrix", "/data/raw/matrix")
        assert "The Matrix" in str(result)
        assert str(result).startswith(str(Path(settings.completed_path)))

    def test_title_with_special_chars(self):
        worker = self._make_worker()
        result = worker._determine_output_path('Movie: "Title"', "/data/raw/movie")
        path_str = str(result)
        assert ":" not in Path(path_str).name
        assert '"' not in Path(path_str).name

    def test_lands_directly_under_completed_path(self):
        """The fallback _determine_output_path no longer partitions by
        type (subdir Settings fields were removed in v18.0.0). Output
        lands directly under completed_path; ARM owns the type subdir
        via the webhook output_path."""
        worker = self._make_worker()
        result = worker._determine_output_path("Test Movie (2024)", "/data/raw/test")
        # Result is exactly completed_path / <leaf>; no intermediate subdir.
        assert result.parent == Path(settings.completed_path)


# --- TranscodeWorker._classify_media_type ---


class TestClassifyMediaType:
    """Tests for _classify_media_type static method."""

    def test_dvd_480p(self):
        from transcoder import TranscodeWorker
        assert TranscodeWorker._classify_media_type(480) == "DVD"

    def test_dvd_576p_pal(self):
        from transcoder import TranscodeWorker
        assert TranscodeWorker._classify_media_type(576) == "DVD"

    def test_bluray_720p(self):
        from transcoder import TranscodeWorker
        assert TranscodeWorker._classify_media_type(720) == "Blu-ray"

    def test_bluray_1080p(self):
        from transcoder import TranscodeWorker
        assert TranscodeWorker._classify_media_type(1080) == "Blu-ray"

    def test_uhd_2160p(self):
        from transcoder import TranscodeWorker
        assert TranscodeWorker._classify_media_type(2160) == "UHD Blu-ray"

    def test_uhd_4320p(self):
        from transcoder import TranscodeWorker
        assert TranscodeWorker._classify_media_type(4320) == "UHD Blu-ray"


# --- TranscodeWorker._format_resolution ---


class TestFormatResolution:
    """Tests for _format_resolution static method."""

    def test_480p(self):
        from transcoder import TranscodeWorker
        assert TranscodeWorker._format_resolution(480) == "480p"

    def test_576p_still_480p_label(self):
        from transcoder import TranscodeWorker
        assert TranscodeWorker._format_resolution(576) == "480p"

    def test_720p(self):
        from transcoder import TranscodeWorker
        assert TranscodeWorker._format_resolution(720) == "720p"

    def test_1080p(self):
        from transcoder import TranscodeWorker
        assert TranscodeWorker._format_resolution(1080) == "1080p"

    def test_2160p(self):
        from transcoder import TranscodeWorker
        assert TranscodeWorker._format_resolution(2160) == "2160p"

    def test_unusual_resolution(self):
        from transcoder import TranscodeWorker
        assert TranscodeWorker._format_resolution(900) == "900p"


# --- TranscodeWorker._get_codec_name ---


class TestGetCodecName:
    """Tests for _get_codec_name method."""

    def _make_and_test(self, video_encoder, overrides=None, expected=None):
        """Create worker and call _get_codec_name within the same patch scope."""
        scheme = _mock_scheme(video_encoder)
        with patch("transcoder.check_gpu_support", return_value=_gpu_support_all()), \
             patch("main.active_scheme", scheme):
            from transcoder import TranscodeWorker
            worker = TranscodeWorker()
            result = worker._get_codec_name(overrides)
        assert result == expected

    def test_nvenc_h265(self):
        self._make_and_test("nvenc_h265", expected="HEVC")

    def test_hevc_nvenc(self):
        self._make_and_test("nvenc_h265", overrides={"video_encoder": "hevc_nvenc"}, expected="HEVC")

    def test_x265(self):
        self._make_and_test("x265", expected="HEVC")

    def test_nvenc_h264(self):
        self._make_and_test("nvenc_h264", expected="H264")

    def test_x264(self):
        self._make_and_test("x264", expected="H264")

    def test_vaapi_h265(self):
        self._make_and_test("vaapi_h265", expected="HEVC")

    def test_qsv_h264(self):
        self._make_and_test("qsv_h264", expected="H264")

    def test_amf_h265(self):
        self._make_and_test("amf_h265", expected="HEVC")


# --- TranscodeWorker._determine_output_path with resolution ---


class TestDetermineOutputPathWithMetadata:
    """Tests for _determine_output_path with resolution metadata."""

    def _run_test(self, video_encoder, title, source, resolution, expected_name):
        scheme = _mock_scheme(video_encoder)
        with patch("transcoder.check_gpu_support", return_value=_gpu_support_all()), \
             patch("main.active_scheme", scheme):
            from transcoder import TranscodeWorker
            worker = TranscodeWorker()
            with patch("transcoder.settings") as s:
                s.completed_path = "/data/completed"
                result = worker._determine_output_path(
                    title, source, resolution=resolution
                )
        assert result.name == expected_name

    def test_dvd_with_year(self):
        self._run_test("nvenc_h265", "Serial-Mom", "/data/raw/Serial-Mom (1994)",
                        (720, 480), "Serial-Mom (1994) 480p DVD HEVC")

    def test_bluray_1080p_with_year(self):
        self._run_test("nvenc_h265", "Some Movie", "/data/raw/Some Movie (2020)",
                        (1920, 1080), "Some Movie (2020) 1080p Blu-ray HEVC")

    def test_uhd_2160p_with_year(self):
        self._run_test("nvenc_h265", "Big Film", "/data/raw/Big Film (2023)",
                        (3840, 2160), "Big Film (2023) 2160p UHD Blu-ray HEVC")

    def test_no_year_in_source(self):
        self._run_test("nvenc_h265", "Unknown Movie", "/data/raw/Unknown Movie",
                        (1920, 1080), "Unknown Movie 1080p Blu-ray HEVC")

    def test_no_resolution_with_year(self):
        self._run_test("nvenc_h265", "Fallback Movie", "/data/raw/Fallback Movie (2021)",
                        None, "Fallback Movie (2021)")

    def test_no_resolution_no_year(self):
        self._run_test("nvenc_h265", "Plain Movie", "/data/raw/Plain Movie",
                        None, "Plain Movie")

    def test_h264_codec(self):
        self._run_test("nvenc_h264", "H264 Movie", "/data/raw/H264 Movie (2022)",
                        (1920, 1080), "H264 Movie (2022) 1080p Blu-ray H264")

    def test_tv_show_with_resolution(self):
        """Even for what looks like a TV show title, the legacy fallback
        no longer partitions output by type - that responsibility is
        ARM's via output_path. Just assert the name format is correct."""
        scheme = _mock_scheme("nvenc_h265")
        with patch("transcoder.check_gpu_support", return_value=_gpu_support_all()), \
             patch("main.active_scheme", scheme):
            from transcoder import TranscodeWorker
            worker = TranscodeWorker()
            with patch("transcoder.settings") as s:
                s.completed_path = "/data/completed"
                result = worker._determine_output_path(
                    "Show S01E05", "/data/raw/Show S01E05 (2023)", resolution=(1920, 1080)
                )
        assert result.name == "Show S01E05 (2023) 1080p Blu-ray HEVC"
        assert result.parent == Path("/data/completed")

    def test_720p_resolution(self):
        self._run_test("x265", "HD Movie", "/data/raw/HD Movie (2019)",
                        (1280, 720), "HD Movie (2019) 720p Blu-ray HEVC")


# --- TranscodeWorker._cleanup_source ---


class TestCleanupSource:
    """Tests for _cleanup_source method."""

    def _make_worker(self):
        scheme = _mock_scheme("x265")
        with patch("transcoder.check_gpu_support", return_value=_gpu_support_all()), \
             patch("main.active_scheme", scheme):
            from transcoder import TranscodeWorker
            return TranscodeWorker()

    @pytest.mark.asyncio
    async def test_cleanup_directory(self, tmp_path):
        target = tmp_path / "movie_dir"
        target.mkdir()
        (target / "file.mkv").write_bytes(b"\x00" * 100)
        worker = self._make_worker()
        await worker._cleanup_source(str(target))
        assert not target.exists()

    @pytest.mark.asyncio
    async def test_cleanup_single_file(self, tmp_path):
        target = tmp_path / "movie.mkv"
        target.write_bytes(b"\x00" * 100)
        worker = self._make_worker()
        await worker._cleanup_source(str(target))
        assert not target.exists()

    @pytest.mark.asyncio
    async def test_cleanup_nonexistent(self, tmp_path):
        worker = self._make_worker()
        path = str(tmp_path / "nonexistent")
        await worker._cleanup_source(path)  # Should not raise


# --- TranscodeWorker properties ---


class TestWorkerProperties:
    """Tests for TranscodeWorker properties."""

    def _make_worker(self):
        scheme = _mock_scheme("x265")
        with patch("transcoder.check_gpu_support", return_value=_gpu_support_all()), \
             patch("main.active_scheme", scheme):
            from transcoder import TranscodeWorker
            return TranscodeWorker()

    def test_initial_state(self):
        worker = self._make_worker()
        assert worker.is_running is False
        assert worker.queue_size == 0
        assert worker.current_job is None

    def test_shutdown_sets_event(self):
        worker = self._make_worker()
        assert not worker._shutdown_event.is_set()
        worker.shutdown()
        assert worker._shutdown_event.is_set()


# --- TranscodeWorker._get_video_resolution ---


class TestGetVideoResolution:
    """Tests for _get_video_resolution method."""

    def _make_worker(self):
        scheme = _mock_scheme("x265")
        with patch("transcoder.check_gpu_support", return_value=_gpu_support_all()), \
             patch("main.active_scheme", scheme):
            from transcoder import TranscodeWorker
            return TranscodeWorker()

    @pytest.mark.asyncio
    async def test_valid_output_parsed(self):
        """Should parse ffprobe output into (width, height) tuple."""
        worker = self._make_worker()
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"1920x1080\n", b""))

        with patch("transcoder.asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)):
            result = await worker._get_video_resolution(Path("/fake/video.mkv"))

        assert result == (1920, 1080)

    @pytest.mark.asyncio
    async def test_4k_resolution(self):
        """Should parse 4K resolution correctly."""
        worker = self._make_worker()
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"3840x2160\n", b""))

        with patch("transcoder.asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)):
            result = await worker._get_video_resolution(Path("/fake/video.mkv"))

        assert result == (3840, 2160)

    @pytest.mark.asyncio
    async def test_dvd_resolution(self):
        """Should parse DVD resolution correctly."""
        worker = self._make_worker()
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"720x480\n", b""))

        with patch("transcoder.asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)):
            result = await worker._get_video_resolution(Path("/fake/video.mkv"))

        assert result == (720, 480)

    @pytest.mark.asyncio
    async def test_ffprobe_failure_returns_none(self):
        """Should return None when ffprobe fails."""
        worker = self._make_worker()

        with patch("transcoder.asyncio.create_subprocess_exec", AsyncMock(side_effect=FileNotFoundError)):
            result = await worker._get_video_resolution(Path("/fake/video.mkv"))

        assert result is None

    @pytest.mark.asyncio
    async def test_malformed_output_returns_none(self):
        """Should return None when ffprobe output is malformed."""
        worker = self._make_worker()
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"garbage\n", b""))

        with patch("transcoder.asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)):
            result = await worker._get_video_resolution(Path("/fake/video.mkv"))

        assert result is None

    @pytest.mark.asyncio
    async def test_empty_output_returns_none(self):
        """Should return None when ffprobe returns empty output."""
        worker = self._make_worker()
        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        with patch("transcoder.asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)):
            result = await worker._get_video_resolution(Path("/fake/video.mkv"))

        assert result is None


# --- HandBrake preset selection by resolution ---


class TestHandBrakePresetSelection:
    """Tests for resolution-based preset selection in _transcode_file_handbrake."""

    async def _run_handbrake(self, resolution, tmp_path):
        """Create worker and run _transcode_file_handbrake within active_scheme patch."""
        scheme = _mock_scheme("nvenc_h265")
        output = tmp_path / "test_out.mkv"
        captured = []

        async def capturing_exec(*args, **kwargs):
            captured.append(args)
            output.touch()
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.stdout = AsyncMock()
            mock_proc.stdout.__aiter__ = lambda self: self
            mock_proc.stdout.__anext__ = AsyncMock(side_effect=StopAsyncIteration)
            mock_proc.stdout.read = AsyncMock(return_value=b"")
            mock_proc.wait = AsyncMock(return_value=0)
            return mock_proc

        with patch("transcoder.check_gpu_support", return_value=_gpu_support_all()), \
             patch("main.active_scheme", scheme):
            from transcoder import TranscodeWorker
            worker = TranscodeWorker()
            with patch.object(worker, "_get_video_resolution", AsyncMock(return_value=resolution)), \
                 patch("transcoder.asyncio.create_subprocess_exec", capturing_exec):
                await worker._transcode_file_handbrake(
                    Path("/fake/video.mkv"), output, 1
                )

        return captured[0]

    @pytest.mark.asyncio
    async def test_4k_source_uses_4k_preset(self, tmp_path):
        """4K source (>1080p) should use the uhd tier preset."""
        cmd = await self._run_handbrake((3840, 2160), tmp_path)
        preset_idx = cmd.index("--preset")
        assert cmd[preset_idx + 1] == "Test 2160p 4K"

    @pytest.mark.asyncio
    async def test_1080p_source_uses_standard_preset(self, tmp_path):
        """1080p source should use the bluray tier preset."""
        cmd = await self._run_handbrake((1920, 1080), tmp_path)
        preset_idx = cmd.index("--preset")
        assert cmd[preset_idx + 1] == "Test 1080p"

    @pytest.mark.asyncio
    async def test_480p_source_adds_upscale(self, tmp_path):
        """DVD source (<720p) should use dvd tier preset with --width 1280."""
        cmd = await self._run_handbrake((720, 480), tmp_path)
        preset_idx = cmd.index("--preset")
        assert cmd[preset_idx + 1] == "Test 720p"
        assert "--width" in cmd
        width_idx = cmd.index("--width")
        assert cmd[width_idx + 1] == "1280"

    @pytest.mark.asyncio
    async def test_ffprobe_failure_uses_standard_preset(self, tmp_path):
        """When resolution detection fails, should fall back to bluray tier preset."""
        cmd = await self._run_handbrake(None, tmp_path)
        preset_idx = cmd.index("--preset")
        assert cmd[preset_idx + 1] == "Test 1080p"

    @pytest.mark.asyncio
    async def test_720p_source_uses_standard_preset(self, tmp_path):
        """720p source (boundary) should use bluray tier preset without upscale."""
        cmd = await self._run_handbrake((1280, 720), tmp_path)
        preset_idx = cmd.index("--preset")
        assert cmd[preset_idx + 1] == "Test 1080p"
        assert "--width" not in cmd


# --- Disk space pre-check in _process_job ---


class TestDiskSpacePreCheck:
    """Tests for disk space pre-check in _process_job."""

    def _make_worker(self):
        scheme = _mock_scheme("x265")
        with patch("transcoder.check_gpu_support", return_value=_gpu_support_all()), \
             patch("main.active_scheme", scheme):
            from transcoder import TranscodeWorker
            return TranscodeWorker()

    @pytest.mark.asyncio
    async def test_insufficient_disk_space_fails_job(self, tmp_dirs):
        """Job should fail with disk space error when space is insufficient."""
        from contextlib import asynccontextmanager
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from models import Base, TranscodeJobDB

        db_path = str(tmp_dirs["db_dir"] / "disktest.db")
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        @asynccontextmanager
        async def test_get_db():
            async with session_factory() as session:
                try:
                    yield session
                except Exception:
                    await session.rollback()
                    raise

        source_dir = tmp_dirs["raw"] / "TestMovie"
        source_dir.mkdir()
        (source_dir / "movie.mkv").write_bytes(b"\x00" * 10000)

        async with session_factory() as session:
            from models import JobStatus
            job_db = TranscodeJobDB(
                id=801, title="TestMovie",
                source_path=str(source_dir),
                status=JobStatus.PENDING,
            )
            session.add(job_db)
            await session.commit()
            await session.refresh(job_db)
            job_id = job_db.id

        job = TranscodeJob(
            id=job_id,
            title="TestMovie",
            source_path=str(source_dir),
        )

        worker = self._make_worker()

        mock_disk = MagicMock()
        mock_disk.total = 20 * 1024**3
        mock_disk.used = 19.5 * 1024**3
        mock_disk.free = 0.5 * 1024**3

        with patch("transcoder.get_db", test_get_db), \
             patch("transcoder.settings") as mock_settings, \
             patch("utils.shutil.disk_usage", return_value=mock_disk):
            mock_settings.work_path = str(tmp_dirs["work"])
            mock_settings.raw_path = str(tmp_dirs["raw"])
            mock_settings.completed_path = str(tmp_dirs["completed"])
            mock_settings.delete_source = False
            mock_settings.stabilize_seconds = 0
            mock_settings.minimum_free_space_gb = 10.0
            mock_settings.log_path = str(tmp_dirs["work"])

            await worker._process_job(job)

        async with session_factory() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(TranscodeJobDB).where(TranscodeJobDB.id == job_id)
            )
            job_db = result.scalar_one()
            assert job_db.status == JobStatus.FAILED
            assert "disk space" in job_db.error.lower()

        await engine.dispose()


# --- _load_track_metadata ---


class TestLoadTrackMetadata:
    """Tests for TranscodeWorker._load_track_metadata."""

    def _make_worker(self):
        scheme = _mock_scheme("x265")
        with patch("transcoder.check_gpu_support", return_value=_gpu_support_all()), \
             patch("main.active_scheme", scheme):
            from transcoder import TranscodeWorker
            return TranscodeWorker()

    async def _setup_db(self, tmp_path):
        """Create a test DB engine and session factory."""
        from contextlib import asynccontextmanager
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from models import Base

        db_path = str(tmp_path / "track_meta_test.db")
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        @asynccontextmanager
        async def test_get_db():
            async with session_factory() as session:
                try:
                    yield session
                except Exception:
                    await session.rollback()
                    raise

        return engine, session_factory, test_get_db

    @pytest.mark.asyncio
    async def test_loads_metadata_even_when_not_multi_title(self, tmp_path):
        """Should return track metadata even when multi_title is 0 (ARM controls naming)."""
        import json
        from models import TranscodeJobDB, JobStatus

        engine, session_factory, test_get_db = await self._setup_db(tmp_path)

        async with session_factory() as session:
            job_db = TranscodeJobDB(
                id=802, title="SingleTitle",
                source_path="/data/raw/movie",
                status=JobStatus.PENDING,
                multi_title=0,
                track_metadata=json.dumps([{"track_number": "1", "filename": "t01.mkv"}]),
            )
            session.add(job_db)
            await session.commit()
            await session.refresh(job_db)
            job_id = job_db.id

        worker = self._make_worker()
        with patch("transcoder.get_db", test_get_db):
            result = await worker._load_track_metadata(job_id)

        assert result is not None
        assert "t01" in result
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_returns_none_when_no_track_metadata(self, tmp_path):
        """Should return None when track_metadata is NULL."""
        from models import TranscodeJobDB, JobStatus

        engine, session_factory, test_get_db = await self._setup_db(tmp_path)

        async with session_factory() as session:
            job_db = TranscodeJobDB(
                id=803, title="NoMetadata",
                source_path="/data/raw/movie",
                status=JobStatus.PENDING,
                multi_title=1,
                track_metadata=None,
            )
            session.add(job_db)
            await session.commit()
            await session.refresh(job_db)
            job_id = job_db.id

        worker = self._make_worker()
        with patch("transcoder.get_db", test_get_db):
            result = await worker._load_track_metadata(job_id)

        assert result is None
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_returns_none_for_nonexistent_job(self, tmp_path):
        """Should return None when the job ID does not exist."""
        engine, _session_factory, test_get_db = await self._setup_db(tmp_path)

        worker = self._make_worker()
        with patch("transcoder.get_db", test_get_db):
            result = await worker._load_track_metadata(99999)

        assert result is None
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_returns_none_for_invalid_json(self, tmp_path):
        """Should return None when track_metadata contains invalid JSON."""
        from models import TranscodeJobDB, JobStatus

        engine, session_factory, test_get_db = await self._setup_db(tmp_path)

        async with session_factory() as session:
            job_db = TranscodeJobDB(
                id=804, title="BadJSON",
                source_path="/data/raw/movie",
                status=JobStatus.PENDING,
                multi_title=1,
                track_metadata="not-valid-json{{{",
            )
            session.add(job_db)
            await session.commit()
            await session.refresh(job_db)
            job_id = job_db.id

        worker = self._make_worker()
        with patch("transcoder.get_db", test_get_db):
            result = await worker._load_track_metadata(job_id)

        assert result is None
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_returns_map_keyed_by_filename_stem(self, tmp_path):
        """Should return metadata map keyed by filename stem."""
        import json
        from models import TranscodeJobDB, JobStatus

        engine, session_factory, test_get_db = await self._setup_db(tmp_path)

        tracks = [
            {"track_number": 1, "filename": "title_t01.mkv", "title": "Episode 1"},
            {"track_number": 2, "filename": "title_t02.mkv", "title": "Episode 2"},
        ]
        async with session_factory() as session:
            job_db = TranscodeJobDB(
                id=805, title="MultiTitle",
                source_path="/data/raw/series",
                status=JobStatus.PENDING,
                multi_title=1,
                track_metadata=json.dumps(tracks),
            )
            session.add(job_db)
            await session.commit()
            await session.refresh(job_db)
            job_id = job_db.id

        worker = self._make_worker()
        with patch("transcoder.get_db", test_get_db):
            result = await worker._load_track_metadata(job_id)

        assert result is not None
        assert "title_t01" in result
        assert "title_t02" in result
        assert result["title_t01"]["title"] == "Episode 1"
        assert result["title_t02"]["title"] == "Episode 2"
        assert "_track_1" in result
        assert "_track_2" in result
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_returns_none_for_empty_tracks_list(self, tmp_path):
        """Should return None when tracks list is empty (no entries produce keys)."""
        import json
        from models import TranscodeJobDB, JobStatus

        engine, session_factory, test_get_db = await self._setup_db(tmp_path)

        async with session_factory() as session:
            job_db = TranscodeJobDB(
                id=806, title="EmptyTracks",
                source_path="/data/raw/movie",
                status=JobStatus.PENDING,
                multi_title=1,
                track_metadata=json.dumps([]),
            )
            session.add(job_db)
            await session.commit()
            await session.refresh(job_db)
            job_id = job_db.id

        worker = self._make_worker()
        with patch("transcoder.get_db", test_get_db):
            result = await worker._load_track_metadata(job_id)

        assert result is None
        await engine.dispose()


# --- queue_job multi-title support ---


class TestQueueJobMultiTitle:
    """Tests for queue_job() storing multi_title and track_metadata in DB."""

    def _make_worker(self):
        scheme = _mock_scheme("x265")
        with patch("transcoder.check_gpu_support", return_value=_gpu_support_all()), \
             patch("main.active_scheme", scheme):
            from transcoder import TranscodeWorker
            return TranscodeWorker()

    async def _setup_db(self, tmp_path):
        """Create a test DB engine and session factory."""
        from contextlib import asynccontextmanager
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from models import Base

        db_path = str(tmp_path / "queue_job_test.db")
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        @asynccontextmanager
        async def test_get_db():
            async with session_factory() as session:
                try:
                    yield session
                except Exception:
                    await session.rollback()
                    raise

        return engine, session_factory, test_get_db

    @pytest.mark.asyncio
    async def test_stores_multi_title_true(self, tmp_path):
        """queue_job with multi_title=True should store multi_title=1 in DB."""
        import json
        from sqlalchemy import select
        from models import TranscodeJobDB

        engine, session_factory, test_get_db = await self._setup_db(tmp_path)
        worker = self._make_worker()

        tracks = [
            {"track_number": 1, "filename": "t01.mkv", "title": "Ep 1"},
            {"track_number": 2, "filename": "t02.mkv", "title": "Ep 2"},
        ]

        with patch("transcoder.get_db", test_get_db):
            job_id, created = await worker.queue_job(
                job_id=700,
                source_path="/data/raw/series",
                title="Series",
                multi_title=True,
                tracks=tracks,
            )

        assert created is True

        async with session_factory() as session:
            result = await session.execute(
                select(TranscodeJobDB).where(TranscodeJobDB.id == job_id)
            )
            job_db = result.scalar_one()
            assert job_db.multi_title == 1
            assert job_db.track_metadata is not None
            stored_tracks = json.loads(job_db.track_metadata)
            assert len(stored_tracks) == 2
            assert stored_tracks[0]["filename"] == "t01.mkv"
            assert stored_tracks[1]["title"] == "Ep 2"

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_stores_multi_title_false(self, tmp_path):
        """queue_job with multi_title=False should store multi_title=0 in DB."""
        from sqlalchemy import select
        from models import TranscodeJobDB

        engine, session_factory, test_get_db = await self._setup_db(tmp_path)
        worker = self._make_worker()

        with patch("transcoder.get_db", test_get_db):
            job_id, created = await worker.queue_job(
                job_id=701,
                source_path="/data/raw/movie",
                title="Movie",
                multi_title=False,
                tracks=None,
            )

        assert created is True

        async with session_factory() as session:
            result = await session.execute(
                select(TranscodeJobDB).where(TranscodeJobDB.id == job_id)
            )
            job_db = result.scalar_one()
            assert job_db.multi_title == 0
            assert job_db.track_metadata is None

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_default_multi_title_is_zero(self, tmp_path):
        """queue_job without multi_title arg should default to multi_title=0."""
        from sqlalchemy import select
        from models import TranscodeJobDB

        engine, session_factory, test_get_db = await self._setup_db(tmp_path)
        worker = self._make_worker()

        with patch("transcoder.get_db", test_get_db):
            job_id, created = await worker.queue_job(
                job_id=702,
                source_path="/data/raw/movie",
                title="Movie",
            )

        assert created is True

        async with session_factory() as session:
            result = await session.execute(
                select(TranscodeJobDB).where(TranscodeJobDB.id == job_id)
            )
            job_db = result.scalar_one()
            assert job_db.multi_title == 0
            assert job_db.track_metadata is None

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_tracks_without_multi_title_still_stored(self, tmp_path):
        """Tracks should be stored even if multi_title defaults to False."""
        import json
        from sqlalchemy import select
        from models import TranscodeJobDB

        engine, session_factory, test_get_db = await self._setup_db(tmp_path)
        worker = self._make_worker()

        tracks = [{"track_number": 1, "filename": "t01.mkv"}]

        with patch("transcoder.get_db", test_get_db):
            job_id, created = await worker.queue_job(
                job_id=703,
                source_path="/data/raw/movie",
                title="Movie",
                tracks=tracks,
            )

        assert created is True

        async with session_factory() as session:
            result = await session.execute(
                select(TranscodeJobDB).where(TranscodeJobDB.id == job_id)
            )
            job_db = result.scalar_one()
            assert job_db.multi_title == 0
            assert job_db.track_metadata is not None
            stored = json.loads(job_db.track_metadata)
            assert len(stored) == 1

        await engine.dispose()


# Import settings for use in output path tests
from config import settings  # noqa: E402
