## Contents
1. [Hardware Requirements](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Getting-Started#Hardware-Requirements)
2. [Installation](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Getting-Started#Installation)
3. [Docker Setup](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Getting-Started#Docker-Setup)
4. [Virtual Machine Setup](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Getting-Started#Virtual-Machine-Setup)
5. [ARM Configuration](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Getting-Started#ARM-Configuration)
6. [Additional Hardware Setup](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Getting-Started#Additional-Hardware-Setup)

## Hardware Requirements

Operation of ARM does not require much in the way of system requirements, although it goes with out saying that a faster processor and more memory will rip media much faster. System storage is an important requirement to pay attention to, otherwise jobs will fail whilst processing if storage reaches 100%.
- Host OS:
   - Debian 10 (buster) ***ongoing support dropped end of 2022***
   - Open Media Vault (5.x) ***ongoing support dropped end of 2022***
   - Ubuntu Server 18.04 - Needs Multiverse and Universe repositories ***ongoing support dropped end of 2022***
   - Ubuntu 20.04 - Needs Multiverse and Universe repositories
   - **Might work with other Linux distros but this isn't tested
- Hardware:
   - The below are the minimum requirements to support handbrake transcoding of video files, one of the most intensive part of ARM - [Handbrake requirements](https://handbrake.fr/docs/en/latest/technical/system-requirements.html).
   - Processor:
      - AMD Ryzen, Threadripper, or Epyc
      - Intel Core (6th generation and newer) i3, i5, i7, i9, or equivalent Xeon
   - Free memory:
      - Depends on settings used but as a general guide:
      - 1 GB for transcoding standard definition video (480p/576p)
      - 2 to 8 GB for transcoding high definition video (720p/1080p)
      - 6 to 16 GB or more for transcoding ultra high definition video (2160p 4K)
   - One or more optical drives to rip Blu-Rays, DVDs, and CDs
   (Optional)
   - a (GPU)[#Additional-Hardware-Setup]
- Storage:
   - ARM Docker container 2-4 GB
   - Audio CD: <1GB per CD ripped
   - ARM transcode and completed folders: 10 GB or more recommended for processing and storing your new videos
   - Blurays: requires a minimum of 10-20 GB free space to complete a rip
- Some free time to set everything up


## Installation

ARM can be installed in multiple ways:
- Docker install on a bare metal server/PC
- Docker install in a VM, on a bare metal server/PC
- On a bare metal server/PC ***Note not prefered option***

### Docker Setup

ARM has a prebuilt docker image ready to go with minimal steps required to start, this is the best option for new users of ARM as it requires less setup and configuration - [prebuilt image](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/docker).

The alternative is to build the docker image from the ARM dockerfile on your system and
       - [Build from Dockerfile](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Building-ARM-docker-image-from-source)

### Virtual Machine Setup

Prior to installing ARM within a virtual machine, the VM needs any hardware passed through from the host to the VM such that drive can then be passed through to docker. With multiple layers of obstraction, there is potential to not configure drives correctly which has been known to cause issues with ARM functionality and throw strange errors. Setting up the Host machine will prevent these issues from surfacing. Thanks to [stevenewbs](https://github.com/stevenewbs/blog/blob/master/libvirtd%20qemu%20Blu%20Ray%20passthrough.md) for the setup information.

#### Apparmor

If setup Apparmor may block access to your disk drive so you need to whitelist it.

1. Check if Apparmour is blocking access:

```dmesg | grep /dev/sg0``` OR ```dmesg | grep /dev/sr0```

Check for "DENIED" entries for /dev/s{r,g}0

2. Add lines to /etc/apparmor.d/libvirt/TEMPLATE.qemu to allow access to qemu:

```
    profile LIBVIRT_TEMPLATE flags=(attach_disconnected) {
      #include <abstractions/libvirt-qemu>
      /dev/sg* rwk,
      /dev/sr* rwk,
    }
```

3. Add the /dev... from above to /etc/apparmor.d/usr.lib.libvirt.virt-aa-helper under the # for hostdev section:

```
    ...
    # for hostdev
    /dev/sr* rwk,
    /dev/sg* rwk,
    ...
```

4. Reload apparmor:

```sudo systemctl restart apparmor```

#### Libvirt / qemu config

1. If it does not already exist, create the VM.

2. List SCSI devices to get the ID of any CD, DVD or Bluray drives. These will be identified as an sr[0-9] drive, shown below as sr0 and sr1.

```
$ lsscsi
[0:0:0:0]    disk    ATA      WDC WDS120G2G0A- 0000  /dev/sda
[1:0:0:0]    cd/dvd  HL-DT-ST BDDVDRW CH12LS28 1.00  /dev/sr0
[2:0:0:0]    disk    ATA      KINGSTON SHFS37A BBF2  /dev/sdb
[3:0:0:0]    cd/dvd  PLDS     DVD+-RW DH-16ABS PD11  /dev/sr1
```

3. On the host, edit the VM's config.

```$ sudo virsh edit <VM NAME>```

4. Add a section for a SCSI controller and a new hostdev device. These need to be within the <devices> tags - the file will re-generate with your changes afterwards anyway.

- The below may exist already. If not, add it.

```
  <controller type='scsi' index='0' model='virtio-scsi'>
     <address type='pci' domain='0x0000' bus='0x00' slot='0x0c' function='0x0'/>
  </controller>
```

- Following the above, add a new <hostdev> section for each drive. The adapter name needs to reflect the drive ID as provided from lssci.
sr0 will be scsi_host1
sr1 will be scsi_host3
- Each hostdev entry must have a unique ID otherwise the VM won't load. In the below example sr1 is assigned unit ID of '1'.

```
  <hostdev mode='subsystem' type='scsi' managed='no'>
    <source>
      <adapter name='scsi_host1'/>
      <address bus='0' target='0' unit='0'/>
    </source>
    <readonly/>
    <address type='drive' controller='0' bus='0' target='0' unit='0'/>
  </hostdev>
  <hostdev mode='subsystem' type='scsi' managed='no'>
    <source>
      <adapter name='scsi_host3'/>
      <address bus='0' target='0' unit='0'/>
    </source>
    <readonly/>
    <address type='drive' controller='0' bus='0' target='0' unit='1'/>
  </hostdev>
```

- Save and exit the editor.

5. Boot the VM. Once loaded confirm with lssci that the drives have passed correctly.

```
lsscsi
[0:0:0:0]    cd/dvd  HL-DT-ST BDDVDRW CH12LS28 1.00  /dev/sr0
[0:0:0:1]    cd/dvd  PLDS     DVD+-RW DH-16ABS PD11  /dev/sr1
```

## ARM Configuration

Once setup, ARM operates will operate with no changes to the default configuration. However, to get the most of ARM review the configuration files and modify to suit the media being ripped. See ARM [Configuration](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/Configuring-ARM) for more information.


## Additional Hardware Setup

Ripping media with additional hardware configuration allows for faster transcoding and depending on the host system, should improve ripping times.
Supported Hardware Acceleration:
- Optional extras. None of these are required for ARM to run.
  - For [Intel QuickSync Video support](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/intel-qsv) you need 6th Gen CPU (Skylake) or newer with QuickSync feature set
  - For [AMD VCE support](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/amd-vce) you need RX400, 500, Vega/II, Navi series GPU or better
  - For [NVIDIA NVENC support](https://github.com/automatic-ripping-machine/automatic-ripping-machine/wiki/nvidia) you need GeForce GTX Pascal (1050+) and RTX Turing (1650+, 2060+) series GPU or better

**A small warning, using Intel QuickSync/AMD VCE/NVIDIA NVENC will decrease video quality, but it increases the speed of encoding significantly!**