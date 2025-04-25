# Adding AMD VCE Support

## Hardware/Software Requirements
 - AMD Radeon RX 400, 500, Vega/II, Navi series GPU or better
 - Ubuntu Linux 20.04 or later
 - AMD Radeon Software for Linux version 19.20
 - Manually install the amf-amdgpu-pro package included with the AMD drivers
 - Vulkan SDK

If you have these you can continue...


Currently no distros enable AMD VCE by default in their packages of HandBrake/CLI. Not Even HandBrake themselves have it enabled for linux. It is considered bleeding edge and highly experimental. VCE support needs to be added manually, this means rebuilding HandBrake from source.

## Ubuntu 20.04 - 24.02
I have made a script that will Install all the requirements for Intel QSV & enable AMD VCE from the HandBrake build.
**This is only tested on Ubuntu 20.04** **And BARELY tested on 24.02**
You can either follow along the [commands](https://github.com/automatic-ripping-machine/automatic-ripping-machine/blob/main/scripts/installers/ubuntu-quicksync.sh) or you can run:

 ```
 sudo apt install wget
 wget https://github.com/automatic-ripping-machine/automatic-ripping-machine/blob/main/scripts/installers/ubuntu-quicksync.sh 
 sudo chmod +x ubuntu-quicksync.sh
 sudo ./ubuntu-quicksync.sh
 ```
 Remember to `reboot` to complete installation.
 
This script installs some additional requirements for Intel QSV, and was for Ubuntu if you would like to only enable VCE. 
You can use these commands 

``` 
## Handbrake -  We use this one for the h.264 VCE preset
## The HandBrake repo doesn't include and profiles for VCE h.264
## If you dont need h.264 you can use
###git clone https://github.com/HandBrake/HandBrake.git && cd HandBrake
git clone https://github.com/1337-server/HandBrake.git && cd HandBrake
./configure --disable-gtk --enable-vce --launch-jobs=$(nproc) --launch
sudo make --directory=build install
```

But you will need to make you sure have all the dependencies for your own distro. 

## Other distros/Linux version

You can find full details for your own version from the Official HandBrake Documentation  [**HERE**](https://handbrake.fr/docs/en/1.3.0/developer/build-linux.html)
You will need to install all the dependencies, then run

``` 
## Handbrake -  We use this one for the h.264 VCE preset
## The HandBrake repo doesn't include and profiles for VCE h.264
## If you dont need h.264 you can use
###git clone https://github.com/HandBrake/HandBrake.git && cd HandBrake
git clone https://github.com/HandBrake/HandBrake.git && cd HandBrake
./configure --disable-gtk --enable-qsv --enable-vce --launch-jobs=$(nproc) --launch
sudo make --directory=build install
```


## After installation

`HandBrakeCLI --help | grep -A12 "Select video encoder"`

If VCE is enabled should give something similar to 

```
   -e, --encoder <string>  Select video encoder:
                               x264
                               x264_10bit
                               vce_h264
                               x265
                               x265_10bit
                               x265_12bit
                               vce_h265
                               mpeg4
                               mpeg2
                               VP8
                               VP9
HandBrake has exited.

```

Once you see your encoder is installed correctly you can now set `H.264 VCE 1080p` as your profile in your arm.yaml config and it will use hardware encoding to speed things up.


You will also need to add the arm user to the video & render groups so that arm can access the VCE encoder
```
sudo usermod -a -G video arm 
sudo usermod -a -G render arm
```

## If you want to use the original HandBrake/HandBrake repo

This means you need pull the repo and manually edit [libhb/handbrake/preset_builtin.h](https://github.com/HandBrake/HandBrake/blob/master/libhb/handbrake/preset_builtin.h)
to add a h.264 VCE profile.

If you dont need h.264 you can pull directly from https://github.com/HandBrake/HandBrake

Then you can build HandBrake and use it for ARM.

The full instuctions to build HandBrake for your own distro can be found here [HandBrake Docs](https://handbrake.fr/docs/en/latest/developer/build-linux.html)

## HandBrake Official Documentation 
For more detailed information you can read through the official HandBrake documentation [HandBrake Building for linux](https://handbrake.fr/docs/en/1.3.0/developer/build-linux.html)
