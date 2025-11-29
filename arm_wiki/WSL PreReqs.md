# WSL Pre-Requirements

## Step 1. Install WSL [MS Learn](https://learn.microsoft.com/en-us/windows/wsl/install)
## Step 2. Install usbipd, bind, and attach DVD Drive.

Follow install of usbipd [here](https://github.com/dorssel/usbipd-win?tab=readme-ov-file)
In an Admin privledged CMD, run
```CMD
usbipd list
usbipd bind --busid <busid> & rem insert busid from earlier
```
This shares the USB device and now you can run
```CMD
usbipd attach --wsl --busid <busid>
```
This attachs the USB to the WSL image. If it errors out on you, you're probably missing packages/tools in your WSL image.

## Step 3. (Optional) Update and install components inside WSL image
```bash
sudo apt update
```
```bash
sudo apt install build-essential flex bison libssl-dev libelf-dev libncurses5-dev git
cd WSL2-Linux-Kernel
export KCONFIG_CONFIG=Microsoft/config-wsl
sudo make menuconfig
```
At this point verify the following components are configured
```
Device Drivers ---> SCSI device support --->

<*> SCSI CDROM support

Device Drivers ---> SCSI device support --->

<*> SCSI disk support
```

If not installed, enable them, and follow Step 1 of this [guide](https://www.starwindsoftware.com/blog/enable-block-storage-devices-in-wsl2/)

