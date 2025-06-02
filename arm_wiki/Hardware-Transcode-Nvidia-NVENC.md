# Checking for NVENC support
Nvidia NVENC support comes with HandBrake in some distros, to check first make sure you have at least
- GeForce GTX Pascal (1050+)
- RTX Turing (1650+, 2060+) 
- or later GPU.
- drivers are updated to at least 418.81 or later.

Testing if HandBrake recognizes your GPU - Run

`HandBrakeCLI --help | grep -A12 "Select video encoder"` 
or 
`HandBrakeCLI --help > /tmp/HandBrakeHelp && grep -A12 "Select video encoder" /tmp/HandBrakeHelp`

into your ssh/terminal window

If NVENC is enabled should give something similar to
```
   -e, --encoder <string>  Select video encoder:
                               x264
                               x264_10bit
                               nvenc_h264
                               x265
                               x265_10bit
                               x265_12bit
                               nvenc_h265
                               nvenc_h265_10bit
                               mpeg4
                               mpeg2
                               VP8
                               VP9
HandBrake has exited.
```
You can also check with 
`HandBrakeCLI --version` and it should output

```
[23:37:19] Compile-time hardening features are enabled
[23:37:19] nvenc: version 12.0 is available
[23:37:19] nvdec: is not compiled into this build
[23:37:19] hb_init: starting libhb thread
[23:37:19] thread 7f002300e700 started ("libhb")
HandBrake 20230130172537-a5238f484-master
```

## Cant see those options ?

If you don't see the extra options for nvenc then you will need to build HandBrakeCLI from source.
instructions can be found here: 

First add all the dependencies from here:
https://handbrake.fr/docs/en/latest/developer/install-dependencies-ubuntu.html

and then when ready build handbrake following instructions from here: https://handbrake.fr/docs/en/latest/developer/build-linux.html

## Installing NVIDIA drivers:
We recommended to do a driver update immediately after installing ubuntu

1. Installing the drivers on servers and/or for computing purposes
`sudo ubuntu-drivers install --gpgpu`
If you have a desktop environment install drop the --gpgpu

2. Reboot system
`sudo reboot`

## Installing NVIDIA drivers directly:
If HandBrakeCLI lists the encoder but throws an error like:
`Driver does not support the required nvenc API version. Required: 13.0 Found: 12.1`
you can install the latest driver from Nvidia directly to helpfully get a newer version of the driver

1. Find the correct version of driver from https://www.nvidia.com/en-us/drivers/ to your server.
2. Download the vendor provided installer 
e.g. : `wget https://us.download.nvidia.com/XFree86/Linux-x86_64/570.144/NVIDIA-Linux-x86_64-570.144.run`

3. Install the driver with admin privilages:
`sudo bash ./NVIDIA-Linux-x86_64-570.144.run`

4. Follow the prompts.

5. Reboot system
`sudo reboot`

## Installing the NVIDIA Container Toolkit:
Do this before point 5 in post installation guide for docker "Run the container with sudo ./start_arm_container.sh" 

1. Adding the repository:
```
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
  && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
```
    
2. Update repository
`sudo apt-get update`
4. Install the NVIDIA Container Toolkit packages:
`sudo apt-get install -y nvidia-container-toolkit`

5. Configure the container runtime by using the nvidia-ctk command:
`sudo nvidia-ctk runtime configure --runtime=docker`

6. Restart the Docker daemon:
`sudo systemctl restart docker`


## Post install

Once handbrake recognizes your GPU,
You can use one of the 2 built in profiles in your arm.yaml config.

`H.265 NVENC 2160p 4K` OR `H.265 NVENC 1080p`


You will also need to add the arm user to the video & render groups so that arm can access the NVENC encoder
```
sudo usermod -a -G video arm 
sudo usermod -a -G render arm
```

------
## 🐋 - NVENC doesn't work

Be sure that both variables for `NVIDIA_DRIVER_CAPABILITIES=all`
and `--gpus all` are set as NVENC won't work without them

## HandBrake Official Documentation 
For more detailed information you can read through the official HandBrake documentation [HandBrake Building for linux](https://handbrake.fr/docs/en/1.3.0/developer/build-linux.html)

