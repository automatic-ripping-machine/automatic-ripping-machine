# Automatic Ripping Machine and MakeMKV
A.R.M. uses MakeMKV under the hood to decrypt and copy the content of optical disks (DVDs and Blu-rays).  You can find 
more information about MakeMKV in the links below.

* [MakeMKV Website](https://www.makemkv.com/)
* [MakeMKV EULA (End User Licence Agreement)](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/MakeMKV-EULA)
* [MakeMKV Forums](https://forum.makemkv.com/forum/)

## MakeMKV Licence
MakeMKV is free while in Beta.  However, if you wish to support this wonderful project you can do so by purchasing a 
licence from MakeMKV here: https://www.makemkv.com/buy/

If you purchased a licence key, you can enter it in the A.R.M. settings by navigating to your A.R.M. installation, 
choose "Arm Settings" from the navigation bar, go to the "Ripper Settings" tab and scroll down to the 
"MAKEMKV_PERMA_KEY" field.  In this field enter your purchased licence key. A.R.M. will make use going forward.  
If you leave the feild empty, A.R.M. will use a Beta key instead.

## MakeMKV Settings
MakeMKV uses the concept of profiles to decide which audio tracks and which subtitle tracks to include in the 
*.mkv files. The defaults are usually sufficient. However, A.R.M. allows you to change these defaults if needed.  This is 
considered advance usage of MakeMKV and A.R.M. The list below contains some information as to where to start, these 
are links to MakeMKV forum pages.
* [Conversion Profiles](https://forum.makemkv.com/forum/viewtopic.php?f=10&t=4385)
* [Changing Default Track Selection](https://forum.makemkv.com/forum/viewtopic.php?f=10&t=4386)
* [Changing Default Track Order In Output File](https://forum.makemkv.com/forum/viewtopic.php?f=10&t=4566)

You can use the information above to learn how to create an MakeMKV conversion profile xml file.  You can then go to 
your A.R.M. installation URL, choose "Arm Settings" from the navigation bar, go to the "Ripper Settings" tab and scroll 
down to the MKV_ARGS field. In this field enter `--profile=/<path-to-your-custom-makemkv-profile.mmcp.xml>` Note that 
the file location must be accessible by the arm user and must be owned by the arm user (or at the very least readable). 
It is recommended to place it in the `/home/arm/` directory.