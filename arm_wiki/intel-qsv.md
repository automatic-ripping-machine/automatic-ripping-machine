# Adding Intel QuickSync Support

Some distros may not enable Intel QuickSync Video by default in their packages of HandBrakeCLI. This needs to be added manually, this means rebuilding HandBrake from source.
You can check if your version already came with QSV support by running 

`HandBrakeCLI --help | grep -A12 "Select video encoder"`

If QSV is enabled should give something similar to 

```
   -e, --encoder <string>  Select video encoder:
                               x264
                               x264_10bit
                               qsv_h264
                               x265
                               x265_10bit
                               x265_12bit
                               qsv_h265
                               mpeg4
                               mpeg2
                               VP8
                               VP9
HandBrake has exited.

```

If you don't see `qsv_h264` or `qsv_h265` your version of HandBrakeCLI might not have have QSV enabled when it was built. 
This also could be that you don't have Intel Media SDK installed.

The Intel Media SDK is required for QSV with HandBrake to work.

So you can either try to find the Intel Media SDK package from your distro or you can build it from source.

I have made a script that will Install all the requirements for Intel QSV to get up and running.

You can either follow along the [commands](https://raw.githubusercontent.com/automatic-ripping-machine/automatic-ripping-machine/main/scripts/ubuntu-quicksync.sh) or you can run:

 ```
 sudo apt install wget
 wget https://github.com/automatic-ripping-machine/automatic-ripping-machine/blob/main/scripts/ubuntu-quicksync.sh
 sudo chmod +x ubuntu-quicksync.sh
 sudo ./ubuntu-quicksync.sh
 ```
 Remember to `reboot` to complete installation.


## After Installation
Once you have verified everything installed correctly and the `qsv_264` or `qsv_265` show up when you run the HandBrakeCLI command above. You can set your profile in your arm.yaml config.

There are 2 supported profiles for Intel QSV they are `H.265 QSV 1080p` OR `H.265 QSV 2160p 4K`

You will also need to add the arm user to the video & render groups so that arm can access the QSV encoder
```
sudo usermod -a -G video arm 
sudo usermod -a -G render arm
```
## HandBrake Official Documentation 
For more detailed information you can read through the official HandBrake documentation [HandBrake Building for linux](https://handbrake.fr/docs/en/1.3.0/developer/build-linux.html)

You can also use the flat-packs provided by HandBrake - More information from here [Flatpacks](https://handbrake.fr/docs/en/1.3.0/developer/flatpak-repo.html)