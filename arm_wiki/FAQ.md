# Frequently asked questions

## My arm wont start when i insert a disc ?

When a disc is inserted, udev rules should launch a script (scripts/arm_wrapper.sh) that will launch A.R.M.  Here are some basic troubleshooting steps:
- Look for empty.log.  
  - Everytime you eject the cdrom, an entry should be entered in empty.log like:
  ```
  [2018-08-05 11:39:45] INFO A.R.M: main.<module> Drive appears to be empty or is not ready.  Exiting A.R.M.
  ```
  - Empty.log should be in your logs directory as defined in your arm.yaml file.  If there is no empty.log file, or entries are not being entered when you eject the cdrom drive, then udev is not launching A.R.M correctly.  Check the instructions and make sure the symlink to 51-automedia.rules is set up right.  I've you've changed the link or the file contents you need to reload your udev rules with:
  ```
  sudo udevadm control --reload-rules 
  ```
- Make sure the user arm has write permission to the location you have set in your arm.yaml
    You can test these permissions by inserting a disc and running (remember to replace sr0 with the name of your own device)
	
    `sudo -u arm /usr/bin/python3 /opt/arm/arm/ripper/main.py -d sr0`

- Check that  the arm_wrapper.sh is executable
  try running `tail -f /var/log/syslog` before you insert a disc, then watch for

  `sr0: Process '/opt/arm/scripts/arm_wrapper.sh sr0' failed with exit code 1`

  If you see this in your logs it can mean arm_wrapper.sh isn't executable, you can fix this by running
   
  `sudo chmod +x /opt/arm/scripts/arm_wrapper.sh`

- Lastly is to check the output of `tail -f /var/log/syslog`
  A.R.M may be starting, erroring out and then sending an email before it exits. Check the arm user email for any status messages. You can use the command line 'mail' command to read these. Its rudimentary but it will give any error messages stopping A.R.M from running.

## Is there a way to disable HandBrake encoding, I just want to rip the whole feature leaving it a .mkv file.

You can either edit the arm.yaml manually with: `sudo nano /opt/arm/arm.yaml` or you can use the A.R.M settings page to update

`SKIP_TRANSCODE: false`

Change false to true

`Save the changes to arm.yaml (Ctr + S  then Ctr + x) or pressing submit on the A.R.M settings page

## A.R.M won't eject the DVD until it finishes transcoding

To enable stacking of DVD's there are a couple of settings that must be changed
 - `RIPMETHOD: "mkv"` and `MAINFEATURE: false`
 - Rip method being set to mkv tells arm to use MakeMKV to pull the contents to disk(the raw folder), by default arm will try to transcode straight from the disc
 - Main feature being turned off tells arm that it wants everthing from the disc and not just the main feature.

The reason these aren't enabled by default is that Rip method being set to mkv can cause issues with blurays

## I can't get Intel QuickSync to work

- To check if **Intel QuickSync** is enabled and is set up correctly you can run
   ```
    HandBrakeCLI --help | grep -A12 "Select video encoder"
   ```
  You should see some entries with
  ```
  qsv_265
  qsv_264
  ```
 If none of these are showing, you need to install Intel Media SDK [MediaSDK](https://github.com/Intel-Media-SDK/MediaSDK) and its requirements & install the correct driver for your graphics. **You also may need to recompile HandBrake from source depending on your distro**

- If they are showing are you using the correct profile ? For QSV there are 2 built in profiles you can use 

  - `H.265 QSV 2160p 4K`
  - `H.265 QSV 1080p`

- You can use HandBrakeCLI -z to show all the profiles available

## I cant get AMD VCE to work

- To check if **AMD VCE** is enabled and is set up correctly you can run
   ```
    HandBrakeCLI --help | grep -A12 "Select video encoder"
   ```
  You should see some entries with
  ```
  vce_h264
  vce_h265
  ```
 If none of these are showing, you need to install the amdgpu-pro drivers & amf-amdgpu-pro package. You will also need to install the Vulkan SDK. 

- If they are showing are you using the correct profile ? For VCE there is only 1 built in profiles you can use 
  - `H.264 VCE 1080p`

- Make sure you only install drivers for your own graphics card. Installing incorrect drivers can cause issues with AMD VCE (personally mesa-vulkan-drivers caused a headache, your own may vary)

- Did you compile HandBrakeCLI from source ? Currently, VCE in not enabled by default by any distro. To enable VCE you **MUST** Compile HandBrake from source with the `--enable-vce` flag set. You can see an example of the code [HERE](https://github.com/1337-server/automatic-ripping-machine/blob/v2.2_dev_ubuntu/scripts/installers/ubuntu-quicksync.sh)


## I cant get NVIDIA NVENC to work
 - I have no idea, and I can't test.
 - Consider installing the latest driver from Nvidia and checking for certain your
 - Have you checked our Nvidia notes [here](nvidia)

## Other problems
- Check A.R.M log files 
  - The default location is /home/arm/logs/ (unless this is changed in your arm.yaml file) and is named after the dvd. These are very verbose.  You can filter them a little by piping the log through grep.  Something like 
  ```
  cat <logname> | grep ARM:
  ```  
    This will filter out the MakeMKV and HandBrake entries and only output the A.R.M log entries.
  - You can change the verbosity in the arm.yaml file.  DEBUG will give you more information about what A.R.M is trying to do.  Note: please run a rip in DEBUG mode if you want to post to an issue for assistance.  
  - Ideally, if you are going to post a log for help, please delete the log file, and re-run the disc in DEBUG mode.  This ensures we get the most information possible and don't have to parse the file for multiple rips.

If you need any help feel free to open an issue.  Please see the above note about posting a log.
