## Pre-release - V2.6.4
* drop github actor as it breaks packages by @1337-server in https://github.com/automatic-ripping-machine/automatic-ripping-machine/pull/528
* Update to 2.6.4 by @1337-server in https://github.com/automatic-ripping-machine/automatic-ripping-machine/pull/536

Fixes 
- 1337-server/automatic-ripping-machine#201
- 1337-server/automatic-ripping-machine#203
- 1337-server/automatic-ripping-machine#207
- 1337-server/automatic-ripping-machine#180 now fully saves
- [Fix ARM UI tests](https://github.com/1337-server/automatic-ripping-machine/commit/dfcd69b211b91abf921489e11f7d9ad5e4121eaf) Now correctly moves file, so testing doesn't fail
- Added test to check for breakages for Ubuntu 18
- Fix for scheduled actions not building docker image correctly
- Adds support for sr0-sr9 in docker
- Re-adds support for MakeMKV key in docker
### Python version bumps
- [Bump beautifulsoup4 from 4.10.0 to 4.11.1](https://github.com/1337-server/arm-dependencies/commit/901f64457d77673a2d96cad7adc91cbab5ee327c)
- [Bump soupsieve from 2.3.1 to 2.3.2.post1](https://github.com/1337-server/arm-dependencies/commit/df63d3e206fda5b417f3287c7f56cae628a7d318)
- [Bump cffi from 1.15.0 to 1.15.1 ](https://github.com/1337-server/arm-dependencies/commit/f3aca97bc978d2e3357f32b41783044bb4091835)
- [Bump flask-wtf from 1.0.0 to 1.0.1 ](https://github.com/1337-server/arm-dependencies/commit/24283a8979380f0011ef0b810641c6fe7f7b50b7)
- [Bump xmltodict from 0.12.0 to 0.13.0 ](https://github.com/1337-server/arm-dependencies/commit/cdc92461cf1c527ab210f683a52e3a8f583a0280)
- [Bump sqlalchemy from 1.4.32 to 1.4.39](https://github.com/1337-server/arm-dependencies/commit/e9c08f6f790d30b2d396c303396784b7dd65f874)
- [Bump psutil from 5.9.0 to 5.9.1 ](https://github.com/1337-server/arm-dependencies/commit/4c830553911d050f72776a699aa1d5c879672ab0)
- [Bump apprise from 0.9.7 to 0.9.9 ](https://github.com/1337-server/arm-dependencies/commit/3d1e4e5fe426fdc15fededade8d32c6bfdb8ea34)
- [Bump urllib3 from 1.26.9 to 1.26.10 ](https://github.com/1337-server/arm-dependencies/commit/00ab6de0f7c51fed12303708bee7b0f30988fcb1)
- [Bump certifi from 2021.10.8 to 2022.6.15 ](https://github.com/1337-server/arm-dependencies/commit/80c4cc36357a1a8e54020c7214a891c35f3ee079)
- [Bump actions/setup-python from 2 to 4 ](https://github.com/1337-server/arm-dependencies/commit/b478e5ef251e6ed0ac86893037090b526e4e9369)


## v2.6.0 > v2.6.3
   - Fixed Ubuntu 18 support
   - Added submodule for arm dependencies
   - Added port param to install script
   - Fixed 1337-server/automatic-ripping-machine#126
   - Fixed 1337-server/automatic-ripping-machine#143
   - Fixed 1337-server/automatic-ripping-machine#154
   - Fixed 1337-server/automatic-ripping-machine#155
   - Fixed 1337-server/automatic-ripping-machine#157
   - Fix for modal not showing fixperms text
   - Added helper note/comment for makemkv codes
   - Added git version to logging
   - import_movies() refactored to be a little more readable
   - Messages on database.html now follow the scroll position
   - Refactored save_settings() to comply with sonarcloud
   - send_movies.html now mostly client side, to save long page load times
   - yes/no database buttons are now hidden when getting success/failed jobs 
   - MakeMKV now fully respects the minlength from cfg (MakeMKV was ignoring anything below 2 mins)
   - Music disc now eject on success or failure (eject removed from default abcde.config)
   - Converted all js strings to template strings

## v2.6.0
   - Fixes #129 (Jobs arent removed from index when completed)
   - Added MakeMKV progress in armui
   - Added function to automatically update MakeMKV beta key
   - Restructuring of makemkv.py, code cleanup and formatting
   - Refactoring js code to reduce warnings/errors
   - Refactoring of makemkv.py
       - Fix bug in file sorting
       - Added noqa tags for variables that aren't being used
       - Removing unused variables from makemkv
       - Nicer printing of the logging statement
       - Make sure each title is transcoded in order

   - Updated Ubuntu install scripts
       - ---------- FIXES ----------
       - fixed command to run under arm user & properly run without hanging script
       - fixed errors and added logic
       - Fixed permissions issue
       - fixed out of order parameters
       - fix for broken service start
       - fix for 1337-server/automatic-ripping-machine issue #111 (Permissions error when editing the ARM Settings after fresh install)
       - fix continuing error calling aplay in scripts
       - ---------- ADDED ----------
       - Added pycharm-community install
       - Added ALSA install to script to avoid breakage on Ubuntu Server instances
       - Added handling for arm group/user already existing
       - Added installs for lsscsi and net-tools
       - Added coloration to logging statements
       - Added Markdown v3.3.4 explicitly to requirements.txt, to fix breaking change caused by 3.3.5 (see Python-Markdown/markdown#1203)
       - Added logic to prevent duplicating fstab entries
       - Added handling harness for script options
       - Added logic to run proper installation function
       - Added call for launch_setup
       - Added now shows the ip of the site that's now running
       - ---------- MOVED ----------
       - Moved dev environment installation location
       - Moved heredocs to custom files
       - Moved checkout command a better spot
       - ---------- OTHER ----------
       - pycharm runs as "other", so the 777 is needed
       - implemented install_arm_dev_env
       - implemented launch_setup
       - hard-coding path since the user folder is already created
       - Refactored to run in correct dirs

## v2.5.5
- Added config for Machine Name and option to add to Notifications
- Added option to include Job ID to notification title
- Added JSON notification option
- Added option to have Child servers display on Home Screen (includes Name from above)
- Added Flask CORS (to allow cross-domain fetching for Child server status)
- Added Eject to Abandon
- Added option to check for 99 Track DRM (Mostly Disney DVDs) to arm_wrapper.sh
- Rewrote arm_wrapper.sh to eliminate duplicate tasks. #82 
- Incorporated upstream changes to install scripts (password can be passed into script, detect latest MakeMKV version)
- Reordered some apt options in install scripts to make it easier to cross-diff quiet/"loud" versions
- Modified install scripts to create /mnt/dev links and fstab entries for all sr devices
- Reloudened Debian install script
- Tested install scripts with Debian 11 and Ubuntu 21. Minor tweaks, added red to Ubuntu
- Cleaned up a LOT of javascript in jobRefresh.js for UI. Modernized, stricter, added child watching


## v2.5.3
   - Added Pagination to database and history pages
   - Updated database page to remove old card format
   - Added support for Android and IOS allowing better display on mobile devices
   - Refactored a lot to make things easier to read, large changes to main.py, utils.py, etc
   - DEBUG mode is now the default in the v2_devel branch
   - Re-added ubuntu-quicksync.sh to allow quick install of HW acceleration support
   - Added Update admin password option
   - Bugfix (CD's not ripping)
   - Bugfix (changeparams not showing correct information)
   - Bugfix (arm_wrapper.sh was not executable)
   - Bugfix (remove TMDB_API_KEY and ARM_API_KEY from logging)

## v2.5.2
   - Improved ajax requests for jobs on front page
   - Abandon job now kills the PID (no files are removed)
   - Added chown to ARMui (Fix permissions button)
   - Bypass for forgotten password (WIP)
   - Bugfix (arm_wrapper.sh was not executable)
   - Bugfix (AttributeError when getting failed/successful jobs)
   - Bugfix (sometimes there is no date in a release from mb)

## v2.5.0
  - Only one large item for this version.

    Now added the possibility for users to use [TMDB](https://developers.themoviedb.org/3/getting-started/introduction) as their metadata provider, this only works for movies at the moment. 
    In time this will have the same functionality as OMDB (movies and tv shows)
    The idea driving this is that users should be able to choose their metadata provider.
    I also think this is safer route in the long term, its better to have multiple options than only focus on one provider.
    
    - Added method to let users send/submit their correctly identified movies to a new crc64 API (an api key required)
    - Added check for crc64 from remote database 

## v2.4.6
 - Updated jquery tablesorter, old version was vulnerable to XSS 
 - Removed all unused versions of CSS 
 - Smalls validation checks when searching the database page. (searching now requires min 3 chars)
 - Small changes to index.html (home for arm ui) to warn before abandoning jobs
 - Jquery ui now fully removed. Now uses only bootstrap for theming
 - ARM ui database no longer needs logfiles in url (potentially dangerous), it checks the database instead for the logfile matching the job.
 - Some progress on converting all string types to fstrings where possible
 - ARM will now break out of wait if the user inputs/searches for movie/series.

## v2.3.4 - v2.4.5
 - Adding bypass for db.session.commit() error for movies (WIP only MakeMKV and part of handbrake is coded)
 - Abandon job option added to main ARM ui page (for now this only sets job to failed no processes are cancelled)
 - Typo fixes (ARM ui images has/had some typos these have been updated and corrected)
 - ARM ui now shows CPU temps
 - ARM ui now uses percentage bars to more clearly display storage and RAM usage 
 - ARM ui database page is now fully functional with updated ui that looks clearer and with more details
 - ARM ui database is now searchable
 - ARM ui settings page now fully works and saves your settings to the arm.yaml
 - ARM ui now prevents logfiles that contain "../"
 - ARM ui login page updated to look smoother look
 - Bugfix (ARM will no longer log failures when opening sdx or hdx devices)
 - Bugfix (ARM will no longer crash when dealing with non utf-8 chars)
 - Bugfix (ARM database_updater() was setting incorrect values into the database)
 - Bugfix (ARM ui will no longer crash when trying to read logs with non utf-8 chars)
 - Bugfix (ARM ui will now get the latest % of encode, this was buggy as it was getting the very first % it could find)
 - Bugfix (ARM ui will now correctly display ram usage)
 - Bugfix (ARM ui now correctly deals with setup (it should now create all necessary folders and do so without errors) )
 - Bugfix (ARM ui update title no longer shows html on update)

## v2.3.4
 - Travisci/flake8 code fixes
 - github actions added
 - Bugfix(small bugfix for datadiscs)
 - Bugfix (old versions of yaml would cause Exceptions)
 - Bugfix (db connections are now closed properly for CD's)
 - added bypass for music CD's erroring when trying to commit to the db at the same time

## v2.3.3

 - A smaller more manageable update this time 
 - Early changes for cleaner looking log output
  - Security (HandBrake.py outputs the new prettytable format)
  - Bugfix (Transcode limit is now respected) 
  - Bugfix (Bluray disc with no titles will now be handled correctly and will not throw an exception )
  - Bugfix (abcde.config now correctly uses musicbrainz)

## v2.3.2
 - Added prettytables for logging
 - Remove api/keys from the Config class string printout 
  - Security (HandBrake.py was still outputting all api key and secrets to log file. This has now been fixed)
  - Bugfix (Transcode limit is now respected) 
  - Bugfix (Bluray disc with no titles will now be handled correctly and will not throw an exception ) 

## v2.2.0
 - Added Apprise notifications
  - Added more to the Basic web framework (flask_login)
    - Added login/admin account
    - Added dynamic webserver ip to notifications
    - Allow Deleting entries from the db (also warning for both the page and every delete)
    - Added music CD covers (provided by musicbrainz & coverartarchive.org)
    - Added CPU/RAM info on index page
    - Added some clearer display for the listlogs page 
    - Bugfix (Mainfeature now works when updating in the ui) 
    - Bugfix (Job is no longer added twice when updated in ui) 
    - ALPHA: Added ARM settings page (This only shows settings for the moment, no editing)
  - Added Intel QuickSync Video support
  - Added AMD VCE support
  - Added desktop notifications
  - Added user table to the sqlite db
  - Added Debian Installer Script
  - Added Ubuntu Installer Script
  - Added Auto Identify of music CD's
  - Made changes to the setup logging to allow music CD's to use the their artist name and album name as the log file 
  - Added abcde config file override (This lets you give a custom config file to abcde from anywhere)
  - Added log cleaner function to strip out secret keys (This isn't complete yet)
  - Bugfix (datadiscs with no label no longer fail) 
  - Bugfix (NONE_(timestamp).log will no longer be generated ) 

## v2.1.0
 - Added new package (armui) for web user interface
  - Basic web framework (Flask, Bootstrap)
    - Retitle functionality
    - View or download logs of active and past rips
  - sqlite db

## v2.0.1
 - Fixed crash inserting bluray when bdmt_eng.xml file is not present
 - Fixed error when deleting non-existent raw files
 - Fixed file extension config parameter not being honored when RIPMETHOD='mkv'
 - Fixed media not being moved when skip_transcode=True
 - Added logic for when skip_trancode=True to make it consistent with standard processing
 - Removed systemd and reimplemented arm_wrapper.sh (see Readme for upgrade instructions)

## v2.0.0
 - Rewritten completely in Python
 - Run as non-root
 - Separate HandBrake arguments and profiles for DVD's and Bluray's
 - Set video type or automatically identify
 - Better logging
-  Auto download latest keys_hashed.txt and KEYDB.cfg

## v1.3.0
 - Get Title for DVD and Blu-Rays so that media servers can identify them easily.
 - Determine if video is Movie or TV-Show from OMDB API query so that different actions can be taken (TV shows usually require manual episode identification)
 - Option for MakeMKV to rip using backup method.
 - Option to rip only main feature if so desired.

## v1.2.0
- Distinguish UDF data from UDF video discs

## v1.1.1

- Added devname to abcde command
- Added logging stats (timers). "grep STAT" to see parse them out.

## v1.1.0

- Added ability to rip from multiple drives at the same time
- Added a config file for parameters
- Changed logging
  - Log name is based on ID_FS_LABEL (dvd name) variable set by udev in order to isolate logging from multiple process running simultaneously
  - Log file name and path set in config file
  - Log file cleanup based on parameter set in config file
- Added phone notification options for Pushbullet and IFTTT
- Remove MakeMKV destination directory after HandBrake finishes transcoding
- Misc stuff

## v1.0.1

- Fix ripping "Audio CDs" in ISO9660 format like LOTR.

## v1.0.0

- Initial Release
