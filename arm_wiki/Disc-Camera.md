# Disc Camera

The disc camera feature points a webcam at your drive trays and photographs each disc as the tray closes. The photo is attached to the ARM job, shown in the web UI (home page cards, job detail, history and the title fix pages), copied into the finished rip folder as `disc.jpg`, and, when ARM cannot identify a disc, read with OCR to search for the title.

It gives you a ground-truth record of what was actually inserted, which is handy when the online lookup gets a title wrong or a disc has no usable label.

## How it works

ARM itself only wakes up on the udev `change` event, which fires after the tray has closed and the disc has been read. By then the label is inside the drive. So a small daemon (`arm/camera/daemon.py`) runs all the time:

1. It polls each optical drive's tray state a few times a second (the same `CDROM_DRIVE_STATUS` ioctl the UI uses).
2. It keeps a rolling buffer of the last few seconds of webcam frames.
3. When a tray goes from **open** to anything else, it saves the frame from `CAMERA_LEAD_SECONDS` earlier, i.e. the disc sitting in the open tray just before it retracted, as `DISC_PHOTO_PATH/<srN>_<YYYYmmdd-HHMMSS>.jpg`.
4. A few seconds later udev starts the ripper for that drive. The ripper looks for the newest photo of that drive taken within `DISC_PHOTO_MAX_AGE` seconds and stores its filename on the job.
5. If identification fails, the ripper runs `tesseract` over the photo and tries the largest lines of text as title searches. The raw OCR text is kept on the job and offered on the Title Search / Custom Title pages.
6. After the rip, the photo is copied to the completed folder as `disc.jpg`.

Photos that no job claims (empty-tray closes, ejects) are deleted after `DISC_PHOTO_RETENTION_DAYS`.

## Hardware

- Any UVC USB webcam works (`/dev/video0` on most systems). 720p is plenty; 1080p helps OCR.
- Mount it above the drives looking down at the open trays. One camera can cover two or three drives stacked in a tower; use `CAMERA_DRIVE_REGIONS` to crop each drive's tray out of the frame so each photo only shows its own disc.
- Make sure the trays are lit. Disc labels are reflective, so avoid a light source directly behind the camera.

## Configuration

All settings live in `arm.yaml` (Settings > Ripper Settings in the UI) under the **Disc Camera** heading.

| Key | Default | Meaning |
|---|---|---|
| `CAMERA_ENABLED` | `false` | Turn the daemon on. When false the service stays idle. |
| `CAMERA_DEVICE` | `/dev/video0` | Video device to read. |
| `CAMERA_DRIVES` | blank | Drives to watch, comma separated (`sr0,sr1`). Blank watches every `/dev/sr*`. |
| `CAMERA_DRIVE_REGIONS` | blank | Optional crop per drive: `sr0:x,y,w,h;sr1:x,y,w,h` in frame pixels. |
| `CAMERA_FPS` | `5` | Frames per second kept in the rolling buffer. |
| `CAMERA_BUFFER_SECONDS` | `4` | Seconds of frames kept. Must be larger than the lead time. |
| `CAMERA_LEAD_SECONDS` | `1.5` | How far back from the tray-closed moment to take the photo. |
| `CAMERA_JPEG_QUALITY` | `85` | JPEG quality of saved photos. |
| `DISC_PHOTO_PATH` | `/home/arm/media/disc_photos/` | Where photos are stored. In Docker this is inside the media volume so photos persist. |
| `DISC_PHOTO_MAX_AGE` | `180` | Seconds. A photo older than this when the job starts is not attached. |
| `DISC_PHOTO_RETENTION_DAYS` | `14` | Unattached photos older than this are deleted. |
| `DISC_PHOTO_OCR` | `true` | Run tesseract on the photo when identification fails. |
| `DISC_PHOTO_COPY` | `true` | Copy the photo into the completed rip folder as `disc.jpg`. |

**Tuning the lead time.** Trays take one to two seconds to retract. If your photos show a half-closed tray, raise `CAMERA_LEAD_SECONDS`; if they show the tray before you placed the disc, lower it. Open and close a tray a few times and look at the results in `DISC_PHOTO_PATH`.

**Finding crop regions.** Take a full-frame photo first (leave `CAMERA_DRIVE_REGIONS` blank), open it in an image viewer and note the pixel box around each tray.

## Docker

1. Add the camera to `start_arm_container.sh` (the default script already has it):

   ```bash
   --device="/dev/video0:/dev/video0" \
   ```

2. Set `CAMERA_ENABLED: true` in `arm.yaml` and restart the container. The daemon runs as the `armcamera` runit service inside the container, next to the web UI.

3. **Database upgrade.** This feature adds two columns to the job table. The migration runs when the web UI starts, so after upgrading start the container once and let the UI come up before inserting a disc.

Check it is running:

```bash
docker exec -it arm-rippers sv status armcamera
docker exec -it arm-rippers tail -f /home/arm/logs/camera.log
```

## Bare metal install

The Debian installer installs `tesseract-ocr`, adds `opencv-python-headless` to the venv and installs the `armcamera` systemd unit. On an existing install:

```bash
sudo apt install tesseract-ocr tesseract-ocr-eng
sudo -u arm /opt/arm/venv/bin/pip install -r /opt/arm/requirements.txt
sudo cp /opt/arm/setup/armcamera.service /lib/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now armcamera
```

The `arm` user must be in the `video` group to read the webcam (`sudo usermod -aG video arm`).

## Testing without hardware

The daemon can fake both the camera and the tray event, which is a quick way to check paths and permissions:

```bash
python3 /opt/arm/arm/camera/daemon.py --frames-from /path/to/any.jpg --simulate-close sr0
```

A file named `sr0_<timestamp>.jpg` should appear in `DISC_PHOTO_PATH`.

## Troubleshooting

- **No photos appear.** Check `camera.log`. "Could not open camera" means the device is missing (Docker: check the `--device` line) or the `arm` user cannot read it (group `video`). "tray closed but the frame buffer is empty" means the camera opened but is not delivering frames; try another `CAMERA_DEVICE` or a lower resolution camera.
- **Photos exist but jobs do not show them.** The photo must be of the same drive (`sr0_…` for `/dev/sr0`) and taken less than `DISC_PHOTO_MAX_AGE` seconds before the job started. Check the job log for "Attaching disc photo" or "No disc photo found".
- **Photo is of a closed tray.** Increase `CAMERA_LEAD_SECONDS`.
- **OCR never finds anything.** Run `tesseract /home/arm/media/disc_photos/<file>.jpg stdout` by hand to see what it reads. Better lighting and a crop region help far more than a higher resolution camera.
- **Job fails right after upgrading.** The database has not been migrated yet. Restart the web UI (or the container) once.
