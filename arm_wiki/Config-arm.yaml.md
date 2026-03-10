# The arm.yaml config file

This is the config file for almost all changeable settings of ARM, all of these are very well documented in the file itself.  

The default location for this file is `/etc/arm/config/arm.yaml`
 
However for clarity they are listed here.

They include 

  - UDF disc check
  - Contacting [OMdb](http://www.omdbapi.com/)/auto identify movies or series
  - HandBrake Settings (profile, arguments, and file extention)
  - MakeMKV settings (rip method, arguments)
  - AACS KEYDB download settings (primary site and optional alternate sources)
  - A manual wait time (useful for overriding the OMdb identify or disc mode)
  - Enable or disable ripping of the same disc
  - Media directory settings (identified, unidentified, raw disc files locations)
  - All of the logging level settings and directory
  - The ARM web-server ip and port
  - Emby notification/server details (allowing emby refresh after rips)
  - Notification settings (Pushbullet, IFTTT, Pushover)
  - The location of your [apprise.yaml](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/apprise.yaml) (allows notifications to Discord, Slack, Telegram, Kodi, and lots of others)



You can view the full sample file here  [arm.yaml](https://github.com/automatic-ripping-machine/automatic-ripping-machine/blob/main/setup/arm.yaml)

## AACS / KEYDB options

ARM can automatically download and update the AACS KEYDB.cfg used for Blu‑ray decryption.
This behaviour is controlled entirely from `arm.yaml`:

- **`AACS_KEYDB_ENABLED`**  
  Set to **`true`** to allow ARM to fetch and update KEYDB.cfg. Default is **`false`** so that
  manually added KEYDB files are never overwritten (non‑breaking for existing setups).

- **`AACS_KEYDB_MIN_REFETCH_HOURS`**  
  Minimum hours between fetch attempts (for both the primary URL and extra sources).
  Default is **`24`**. This reduces the risk of being blocked for excessive requests.

- **`AACS_KEYDB_PRIMARY_URL`**  
  Base URL of the primary AACS database site. By default this is  
  `http://fvonline-db.bplaced.net/`.  
  ARM’s `aacs_keydb_download.py` script scrapes this URL for:
  - a `LastUpdate` date, and  
  - `fv_download.php?lang=…` links to zip files containing `keydb.cfg`.  
  If the remote `LastUpdate` is newer than the local `lastupdate.txt`, the script
  downloads the current `KEYDB.cfg` and replaces the local copy.

- **`AACS_KEYDB_EXTRA_SOURCES`**  
  Optional **comma‑separated list** of additional KEYDB sources. Each entry may be:
  - an HTTP/HTTPS URL pointing directly to a `KEYDB.cfg` file, or to a zip archive
    containing `keydb.cfg`, or  
  - a local filesystem path to a `KEYDB.cfg` file or such a zip archive.  

  When `AACS_KEYDB_EXTRA_SOURCES` is **non‑empty**, ARM assumes you have provided
  your own trusted KEYDB sources and:
  - **skips the primary URL entirely**, and  
  - concatenates the contents of all configured sources into the local `KEYDB.cfg`.  

This makes it possible to keep using the default public database when available, or
to switch to your own mirrors / pre‑concatenated KEYDB files via configuration only.