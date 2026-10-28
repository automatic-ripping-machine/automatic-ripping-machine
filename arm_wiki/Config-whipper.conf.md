# The whipper.conf config file

This is the config file for whipper, ARM's secure audio CD ripper. Whipper uses `cdparanoia` (via `libcdio-paranoia`) for bit-perfect digital audio extraction and verifies ripped tracks against the online AccurateRip checksum database.

The default location for this file is `/etc/arm/config/whipper.conf` (or `/opt/arm/setup/whipper.conf`).

## Settings in arm.yaml

Key Whipper behavior is controlled directly from `/etc/arm/config/arm.yaml`:

- `WHIPPER_DRIVE_OFFSET`: Drive read offset sample value (e.g. `667` or `102`). Correct read offset is required for AccurateRip verification.
- `WHIPPER_ACCURATERIP`: When set to `true`, AccurateRip checksum verification is strictly enforced. Set to `false` if ripping rare or self-burned CDs not present in the AccurateRip database.
- `WHIPPER_OUTPUT_FORMAT`: Output format template for tracks (default: `%A/%d/%t - %n`).
- `WHIPPER_DISC_TEMPLATE`: Output format template for disc directory/CUE/log files (default: `%A/%d/%A - %d`).

## Whipper Configuration File

You can also define standalone drive profiles and logging preferences in `/etc/arm/config/whipper.conf`:

```ini
[drive]
# Drive offset can also be configured per-drive
# read_offset = 667

[musicbrainz]
# Server preferences (default is https://musicbrainz.org)
# server = https://musicbrainz.org
```

You can view the full sample file here: [whipper.conf](https://github.com/automatic-ripping-machine/automatic-ripping-machine/blob/main/setup/whipper.conf).
