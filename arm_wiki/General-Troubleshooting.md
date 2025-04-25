# Troubleshooting

## My arm won't start when I insert a disc ?

When a disc is inserted, udev rules should launch a script (scripts/arm_wrapper.sh) that will launch ARM.  Here are some basic troubleshooting steps:
- Look for empty.log.  
  - Every time you eject the CD-ROM, an entry should be entered in empty.log like:
  ```
  [2018-08-05 11:39:45] INFO ARM: main.<module> Drive appears to be empty or is not ready.  Exiting ARM.
  ```
  - Empty.log should be in your logs directory, as defined in your arm.yaml file.  If there is no empty.log file, or entries are not being entered when you eject the CD-ROM drive, then udev is not launching ARM correctly.  Check the instructions and make sure the symlink to 51-automedia.rules is set up right.  I've you've changed the link or the file contents you need to reload your udev rules with:
  ```
  sudo udevadm control --reload-rules 
  ```
- Make sure the user arm has write permission to the locations you have set in your arm.yaml
    You can test these permissions by inserting a disc and running (remember to replace sr0 with the name of your own device)
	
    `sudo -u arm /usr/bin/python3 /opt/arm/arm/ripper/main.py -d sr0`

- Make sure the db file and folder is writeable by the arm user.

    The default location is `/home/arm/db/`

## Disk Tray Opens then Immediately Closes

This can cause a disk to get ripped multiple times in a row,
especially if `ALLOW_DUPLICATES` is `True` (which may be the case for ripping TV shows).

To fix this issue (on systems that use `sysctl`), you can run the following command.
This will create a settings file that disables autoclose on the disk tray,
and reloads sysctl with that settings file.
It requires `root` privileges via `sudo`,
and will persist across reboots.

```bash
printf "# Fix issue with DVD tray being autoclosed after rip is complete\ndev.cdrom.autoclose=0\n" | sudo tee /etc/sysctl.d/arm-uneject-fix.conf >/dev/null && \
  sudo sysctl --load=/etc/sysctl.d/arm-uneject-fix.conf
```

## Other problems
- Check ARM log files 
  - The default location is /home/arm/logs/ (unless this is changed in your arm.yaml file) and is named after the dvd. These are very verbose.  You can filter them a little by piping the log through grep.  Something like
  ```
  cat /home/arm/logs/John_Wick.log | grep ARM:
  ```  
    This will filter out the MakeMKV and HandBrake entries and only output the ARM log entries.
  - You can change the verbosity in the arm.yaml file.  DEBUG will give you more information about what ARM is trying to do.  Note: please run a rip in DEBUG mode if you want to post to an issue for assistance.  
  - Ideally, if you are going to post a log for help, please delete the log file, and re-run the disc in DEBUG mode.  This ensures we get the most information possible and don't have to parse the file for multiple rips.

- If you have no logs, try running `sudo -u arm /usr/bin/python3 /opt/arm/arm/ripper/main.py -d sr0` from a terminal/ssh sometimes this gives information that can't be put into a log (Python coding errors, etc)

If you need any help feel free to open an issue.  Please see the wiki about posting a DEBUG log.

## Changing logging to DEBUG mode
  - Debugging mode is not enabled by default, but it offers a lot more information. If you're experiencing problems the first thing you should do is change logging to DEBUG

  - You can enable Debugging by changing `LOGLEVEL` in your [arm.yaml](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Config-arm.yaml) to `LOGLEVEL: "DEBUG"`

  - This gives a lot more information to help track down any problems.

## Email notifications

A lot of random problems are found in the sysmail, email alerting is a most effective method for debugging and monitoring.

I recommend you install postfix from here:http://mhawthorne.net/posts/2011-postfix-configuring-gmail-as-relay/

Then configure /etc/aliases e.g.:

```	
root: my_email@gmail.com
arm: my_email@gmail.com
userAccount: my_email@gmail.com
```

Run below to pick up the aliases

```
sudo newaliases
```

## UDF support - For users who built their own kernel

If you have built your own kernel, you must add UDF support when compiling or ARM will fail to work.


### If you think you have experienced a new bug, please open an issue.
