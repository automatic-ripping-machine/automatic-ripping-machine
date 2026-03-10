## Configure ARM

ARM's config file is usually located at `/etc/arm/config/arm.yaml`. This path can be changed by advanced users by setting the [environment variable](https://wiki.archlinux.org/title/Environment_variables) `ARM_CONFIG_FILE`.

`arm.yaml` includes explanations for each option. Pay special attention to the 'directory setup' section and make sure the 'arm' user has write access to wherever you define these directories.

In case you want to adjust settings specific to audio CDs, you can find the ABCDE config file at `/etc/arm/config/.abcde.conf` unless configured otherwise in `arm.yaml`.

To allow ARM to identify movie/tv titles, register for an [OMDb API key](http://www.omdbapi.com/apikey.aspx) and set the OMDB_API_KEY parameter in the config file.

### AACS / KEYDB configuration

ARM can keep the AACS `KEYDB.cfg` file up‑to‑date for you. The behaviour is controlled by
options in `arm.yaml` (see also **Config-arm.yaml** for details):

- **`AACS_KEYDB_ENABLED`** – set to `true` to allow auto‑updates; default is `false` so
  manually added KEYDB files are not overwritten.
- **`AACS_KEYDB_MIN_REFETCH_HOURS`** – minimum hours between fetch attempts (default 24)
  to avoid excessive requests to the primary or extra sources.
- **`AACS_KEYDB_PRIMARY_URL`** – the primary AACS database site to scrape for updates.
- **`AACS_KEYDB_EXTRA_SOURCES`** – an optional comma‑separated list of additional URLs or
  local paths that point to pre‑concatenated `KEYDB.cfg` files or zip archives containing
  `keydb.cfg`.

If `AACS_KEYDB_ENABLED` is `true` and `AACS_KEYDB_EXTRA_SOURCES` is left empty, ARM will
use the primary URL to check for a newer database and download it when needed (respecting
the minimum refetch period). If you set one or more extra sources, ARM uses those instead
of the default public site. With `AACS_KEYDB_ENABLED` set to `false`, your manual KEYDB
file is never overwritten.


**Email Notifications**

A lot of random problems are found in the sysmail, email alerting is a most effective method for debugging and monitoring.

I recommend you install postfix from here:http://mhawthorne.net/posts/2011-postfix-configuring-gmail-as-relay/

Then configure /etc/aliases 
	e.g.: 
	
	```	
	root: my_email@gmail.com
	arm: my_email@gmail.com
	userAccount: my_email@gmail.com
	```
	
Run below to pick up the aliases

	```
	sudo newaliases
	```
## Apprise notifications

You can enable Apprise notifications by editing your arm.yaml file. 
You will need to find
 
`APPRISE: ""`

Then add your apprise.yaml file to here like so.

`APPRISE: "/opt/arm/apprise.yaml"`

A sample apprise has been included with arm but is not enabled by default, you can find this file in the doc folder of your arm installation.
You can find how to get the keys/setting up the apprise.yaml from here https://github.com/caronc/apprise/wiki