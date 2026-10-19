# Barcode Scanner

Most DVD and Blu-ray cases carry a UPC/EAN barcode that identifies the exact release. With a cheap USB barcode scanner plugged into the ARM box you can scan the case as you insert the disc. ARM records the code on the job and, when the disc itself cannot be identified, looks the barcode up online to find the title. It is a much more reliable fallback than reading the disc label with the [Disc Camera](Disc-Camera), and the two work together.

## Workflow

1. Scan the barcode on the back of the case.
2. Open the tray, put the disc in, close the tray.
3. ARM starts the job as usual. The barcode is attached to it and shown on the job detail and title fix pages.

The order of scanning and opening the tray does not matter, as long as the scan happens before the tray closes. A scan that is not followed by a tray close within `BARCODE_PAIR_SECONDS` (two minutes by default) is forgotten, so scanning a case and then changing your mind cannot attach the wrong code to the next disc. Scanning twice simply replaces the pending code.

With several drives, whichever tray closes next claims the pending scan.

## How it works

Handheld scanners such as the Eyoyo EY-H2 show up as a USB keyboard and "type" the digits followed by Enter. A headless server has nothing with keyboard focus, so the disc camera daemon (`arm/camera/daemon.py`) reads the scanner directly from its `/dev/input/event*` node with `evdev` and grabs it exclusively, which also stops the digits landing on a console.

1. The daemon keeps the most recent scan in memory.
2. When a drive tray goes from **open** to anything else it writes the code to `DISC_PHOTO_PATH/<srN>_<YYYYmmdd-HHMMSS>.barcode` and forgets the scan.
3. udev starts the ripper for that drive a few seconds later. The ripper looks for the newest `.barcode` file for that drive inside `DISC_PHOTO_MAX_AGE` seconds and stores the code on the job.
4. If normal identification fails, the code is looked up: video discs through [upcitemdb](https://www.upcitemdb.com/) (free, no key, roughly 100 lookups a day), audio CDs through MusicBrainz' release barcode search. The product title is cleaned of packaging words ("Blu-ray + DVD", "2-Disc Set", "Widescreen") and fed into the normal TMDB/OMDb title search. The product title is also kept on the job and offered on the Title Search page.
5. The disc photo OCR fallback, if enabled, runs after the barcode lookup.

Barcode files in `DISC_PHOTO_PATH` are pruned together with unattached photos after `DISC_PHOTO_RETENTION_DAYS`.

## Hardware

Any scanner that works as a USB keyboard (HID) will do; that is the default mode of nearly all of them, including the Eyoyo EY-H2. Leave the scanner in keyboard mode with its default Enter (CR) suffix. A scanner with a stand or auto-sense mode is handy, so you can hold the case in front of it with one hand.

Find the scanner's input node:

```bash
ls -l /dev/input/by-id/
```

The scanner is the `usb-..._...-event-kbd` symlink whose name contains the maker or "Barcode"/"Scanner"; it points at `/dev/input/eventN`. The daemon autodetects a by-id name containing `Eyoyo`, `barcode` or `scanner`; for anything else set `BARCODE_DEVICE`.

The `arm` user needs to be in the `input` group to read it (`sudo usermod -aG input arm`). The installer and the Docker image do this for you.

## Configuration

All settings live in `arm.yaml` (Settings > Ripper Settings in the UI) under the **Barcode Scanner** heading.

| Key | Default | Meaning |
|---|---|---|
| `BARCODE_ENABLED` | `false` | Turn the scanner on. The daemon runs when this or `CAMERA_ENABLED` is true. |
| `BARCODE_DEVICE` | blank | Input node to read (`/dev/input/by-id/usb-...-event-kbd` or `/dev/input/eventN`). Blank autodetects by name. |
| `BARCODE_PAIR_SECONDS` | `120` | How long a scan waits for a tray to close before it is forgotten. |
| `BARCODE_LOOKUP` | `true` | Look the code up online when identification fails. |

`DISC_PHOTO_PATH`, `DISC_PHOTO_MAX_AGE` and `DISC_PHOTO_RETENTION_DAYS` from the [Disc Camera](Disc-Camera) settings apply to barcode files as well.

## Docker

1. Pass the scanner into the container in `start_arm_container.sh`. The by-id symlinks are not available inside the container, so use the `eventN` node it points at:

   ```bash
   --device="/dev/input/event5:/dev/input/event5" \
   ```

2. Set `BARCODE_ENABLED: true` and `BARCODE_DEVICE: "/dev/input/event5"` in `arm.yaml` and restart the container. The daemon runs as the `armcamera` runit service inside the container.

3. **Database upgrade.** This feature adds two columns to the job table. The migration runs when the web UI starts, so after upgrading start the container once and let the UI come up before inserting a disc.

Check it is running:

```bash
docker exec -it arm-rippers sv status armcamera
docker exec -it arm-rippers tail -f /home/arm/logs/camera.log
```

Scan something: the log should show `Barcode scanned: <code> (waiting for a tray to close)`.

## Bare metal install

The Debian installer adds `evdev` to the venv (from `requirements-camera.txt`, together with OpenCV for the camera), puts the `arm` user in the `input` group and installs the `armcamera` systemd unit. On an existing install:

```bash
sudo apt install python3-dev build-essential
sudo -u arm /opt/arm/venv/bin/pip install -r /opt/arm/requirements-camera.txt
sudo usermod -aG input arm
sudo cp /opt/arm/setup/armcamera.service /lib/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now armcamera
```

## Testing without hardware

The daemon can fake a scan and the tray event:

```bash
python3 /opt/arm/arm/camera/daemon.py --scan 085391163926 --simulate-close sr0
```

A file named `sr0_<timestamp>.barcode` containing the code should appear in `DISC_PHOTO_PATH`. Insert a disc in `/dev/sr0` within `DISC_PHOTO_MAX_AGE` seconds and the job will pick it up.

To check the scanner itself, with the daemon stopped:

```bash
sudo -u arm python3 -c "import evdev,sys; d=evdev.InputDevice(sys.argv[1]); print(d.name); [print(evdev.categorize(e)) for e in d.read_loop() if e.type==evdev.ecodes.EV_KEY]" /dev/input/eventN
```

## Troubleshooting

- **"BARCODE_ENABLED is set but no scanner was found".** Autodetection did not recognise the device name. Set `BARCODE_DEVICE` to the right `/dev/input/eventN` (Docker: and pass it through with `--device`).
- **"Permission denied" in camera.log.** The `arm` user is not in the `input` group, or the container does not have the device. Log out and in (or restart the service) after changing groups.
- **Scans show in the log but jobs have no barcode.** The scan must be followed by a tray close on a watched drive within `BARCODE_PAIR_SECONDS`, and the job must start within `DISC_PHOTO_MAX_AGE` seconds of that close. Look for "Attaching barcode" or "No barcode scan found" in the job log.
- **Digits appear on the console instead.** The daemon is not running or has not grabbed the device yet; check `sv status armcamera` / `systemctl status armcamera`.
- **"UPC lookup rate limit reached".** The free upcitemdb endpoint allows about 100 lookups a day per IP. The barcode is still stored on the job and the OCR fallback still runs.
- **Lookup finds the wrong film.** The product title is shown on the job detail page under `disc_barcode`; use Title Search to fix it, the cleaned product title is pre-filled.
