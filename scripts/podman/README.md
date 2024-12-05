This is built off of the dev branch - so I built the container locally
from the automatic-ripping machine git:

podman build . -t arm:latest

This puts the image in your local repo, which is called by these scripts
if you'd like to use the public docker hub container, change the image to

docker.io/automaticrippingmachine/automatic-ripping-machine:latest

Rather than letting arm take control of ~arm, I've directed it to ~arm/arm
this prevents arm from trying to change permissions of ~arm and running into
a bunch of SELinux issues.

This script / quadlet also work with Intel Quicksync as is - I'm passing a 
Intel Corporation Raptor Lake-P [Iris Xe Graphics] into my VM. I have nto tested with
AMD VCN or Nvidia NVENC (yet)
