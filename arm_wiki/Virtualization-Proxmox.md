# Preparing Proxmox-VE 8.1 for A.R.M.

Proxmox-VE is a Virtual Environment platform.  Popular with home-labbers who wish to have multiple services available in 
their home-lab setup.  A.R.M. is an ideal candidate to join this list of services.  However, A.R.M. needs access to the actual
hardware of the computer.  Both the Optical Disk Drive(s) and, if doing Hardware Transcoding, the GPU.  There are two methods 
to accomplish this in Proxmox.  Using a Virtual Machine (VM) or an LXC container.  Both have their advantages and 
disadvantages and depending on your specific situation you may wish to choose one method or the other.  Considerations 
include the hardware you have access to, which other services on your Proxmox machine need access to the same hardware 
resources, and your ability to configure some advanced uses of Proxmox. 

You can, of course, install Docker on the Proxmox Host directly and save yourself a lot of configuration problems but I 
personally prefer to keep my Proxmox Host as "Clean" as possible, and limit the extra packages I install on it to the bare 
minimum needed.

## Proxmox Virtual Machine (VM)
The main advantage of using Virtual Machines is the simplicity.  While it does take some knowledge to properly configure a 
Proxmox VM to pass through all the necessary hardware. The configurations are relatively simple when compared to the LXC 
setup. However, there are some drawbacks, which, depending on the available hardware, make it impossible to use, or 
impractical to use if the same hardware resources are required for some other services.

### Pros
- Simplicity.  Some minor modifications need to be done to the Proxmox host but those are relatively quick
and simple.
- Fewest possible modifications to the Proxmox Host.
- Consistency.  The pass-through process of the hardware for VMs ensures that you have complete control of what the
VM has access to and how.  LXC containers are more finicky and need ongoing maintenance.
- Security.  A VM is more secure than LXC containers, especially since the LXC process requires a lot of removal of the
safety nets that Proxmox puts in place to prevent malicious software from exiting the LXC container.

### Cons
- It is resource intensive.  You need to provide more RAM and CPU power to run a VM since it needs to run a full Linux Kernel
under the hood for your Virtual Machine.
- It also requires dedicated access to the SATA Controller (meaning that the controller
your Optical Drive is connected to needs to be completely given over to the VM.  The other drives that may be connected to the
same controller will no longer be available to Proxmox. (In other words, if you have a SATA SSD or HD connected to your
motherboard and your Optical Drive is also connected to the motherboard, a Proxmox VM is not an option, unless you have a
dedicated PCIe Sata card you can connect your Optical Drive to.)
- If you only have one GPU, and it is of an older model, and you want to do hardware transcoding, you need to give the GPU
entirely to the VM, meaning it is no longer available for any other VMs, LXC containers or even Proxmox itself (Yes Proxmox
uses the GPU)
- Requires newer hardware.  Your CPU needs to support IOMMU, if it does not, you cannot use A.R.M. in a VM.

## Proxmox LXC Container
The main advantage of using an LXC container is the sharability of resources.  But this comes at the cost of complexity to 
set up and maintain.  The passthrough process of hardware of LXC containers is not nearly as straighforward as with VMs.  
That being said, you can passthrough the same device to multiple containers to great effect.  (But I do not suggest 
passing through an  optical disk drive to multiple containers, this may lead to unintended consequences)  An LXC container 
is also inherently not as secure as a VM, but this may not be a consideration if your A.R.M. container will never have 
access to the internet...

### Pros
- Resource light. An LXC container uses the same kernel that Proxmox uses, it simply adds a distribution's "flavour" on top
of it. As such, the amount of RAM and CPU power you need to give A.R.M. is smaller.
- Sharebility of Hardware resources. Because of the way that LXC passes through hardware from the host, that same hardware can
be used by multiple containers.  This is especially useful if you have a Plex/Jellyfin/Emby container and an A.R.M. container
running side by side.
- Runs on older hardware.  A.R.M. has been successfuly installed and used on an Intel Core 2 Duo CPU (which is more then 15
years old as of this writing) While it does run slower then on more modern hardware it does run.  Which is great for putting
that old desktop or laptop to use again instead of going to the landfill.

### Cons
- Complexity.  There is no denying it, configuring Proxmox and your LXC container to run A.R.M. is a complicated process.
However, you will also learn alot about Linux, Proxmox and LXC containers (probably Docker as well) by using an LXC
container.
- Polution of the Proxmox Host.  If you plan to use Hardware Transcoding, you will need to install the drivers for your
GPU on the Proxmox host itself, and then again on the LXC container.
- Requires Special Permission to mount Network Shares. (NFS or Samba)
- Vulnerability. Like Docker containers, the LXC container needs to be a priviledged container, and we also need to loosen
up the apparmor enforcement for the container.  Meaning that if any malicious software were to get in the container, it
could likely break-out of the container relatively easily and then infect your Proxmox machine and all of the attached VMs
and LXC containers and your network.

## Conlusion
There is no correct answer as to which method you eventually choose. Both are valid choices. There are some things that are 
identical for both installation methods, It is strongly suggested that a Network Share be used if you want A.R.M. to 
automaticaly transfer completed rips to a media server (Plex, Jellyfin or Emby) and this is because of too many weird 
errors that can happen if you try to give your LXC container access to the same Volume as your media server for completed 
rips. Below you will find guides for both methods of preparing Proxmox for A.R.M. These methods also include steps for 
Hardware Transcoding with either a Discreet GPU or Integrated GPU. (with the notable exception of the AMD integrated GPUs)

- [Preparing Proxmox Vitual Machines (VM) for A.R.M](#) #TODO
- [Preparing Proxmox LXC Containers for A.R.M.](#) #TODO
