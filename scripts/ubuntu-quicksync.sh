#!/bin/bash
sudo apt update
sudo apt install git
sudo add-apt-repository ppa:oibaf/graphics-drivers
sudo apt update
sudo apt install libvulkan1 vulkan-utils
## WARN! This next line can bork your graphics drivers. care!
# sudo apt install mesa-vulkan-drivers
sudo apt install autoconf libtool xorg xorg-dev openbox libx11-dev libgl1-mesa-glx libgl1-mesa-dev

sudo apt install automake autopoint build-essential cmake git libass-dev libbz2-dev libfontconfig1-dev libfreetype6-dev libfribidi-dev libharfbuzz-dev libjansson-dev liblzma-dev libmp3lame-dev libnuma-dev libogg-dev libopus-dev libsamplerate-dev libspeex-dev libtheora-dev libtool libtool-bin libturbojpeg0-dev libvorbis-dev libx264-dev libxml2-dev libvpx-dev m4 make meson nasm ninja-build patch pkg-config python tar zlib1g-dev 
sudo apt install intel-media-va-driver
 
# INtell quick sync for handbrake
sudo apt-get install -qqy libva-dev libdrm-dev

# only if we want GUI
sudo apt-get install gstreamer1.0-libav intltool libappindicator-dev libdbus-glib-1-dev libglib2.0-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev libgtk-3-dev libgudev-1.0-dev libnotify-dev libwebkit2gtk-4.0-dev



#Libva driver, ubuntu comes with an older version. we need the latest version
git clone https://github.com/intel/libva.git libva
cd libva
./autogen.sh
make
sudo make install

## Intel quicksync HandBrake
wget https://github.com/Intel-Media-SDK/MediaSDK/releases/download/intel-mediasdk-20.3.0/MediaStack.tar.gz
tar -xvf MediaStack.tar.gz
cd MediaStack
sudo chmod +x install_media.sh
sudo ./install_media.sh
cd ..

#intel media sdk # this can fail and not work as it should
git clone https://github.com/Intel-Media-SDK/MediaSDK msdk
cd msdk
mkdir build && cd build
cmake ..
make
sudo make install

## Handbrake -  we use this one for the VCE preset 
git clone https://github.com/HandBrake/HandBrake.git && cd HandBrake
wget https://raw.githubusercontent.com/1337-server/HandBrake/master/libhb/handbrake/preset_builtin.h libhb/handbrake/preset_builtin.h 
./configure --disable-gtk --enable-qsv --enable-vce --launch-jobs=$(nproc) --launch
sudo make --directory=build install

sudo apt update
sudo apt upgrade

sudo usermod -a -G video arm 
sudo usermod -a -G render arm

echo "You should reboot!"
