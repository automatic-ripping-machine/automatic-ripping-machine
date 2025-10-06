#!/bin/bash

# Setup taken from https://github.com/tianon/dockerfiles/blob/master/handbrake/Dockerfile
# The Expat/MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

echo -e "${RED}Finding current HandBrake version${NC}"
HANDBRAKE_VERSION=$(curl --silent 'https://github.com/HandBrake/HandBrake/releases' | grep 'HandBrake/tree/*' | head -n 1 | sed -e 's/[^0-9\.]*//g')
echo -e "${RED}Downloading HandBrake $HANDBRAKE_VERSION${NC}"

# if architecture is any flavor of arm, install standard HandBrakeCLI and exit cleanly
if [[ $(dpkg --print-architecture) =~ arm.* ]]; then
    echo "Running on arm - using apt for HandBrakeCLI"
    exit 0
fi

set -eux
wget -O handbrake.tar.bz2.sig "https://github.com/HandBrake/HandBrake/releases/download/$HANDBRAKE_VERSION/HandBrake-$HANDBRAKE_VERSION-source.tar.bz2.sig"
wget -O handbrake.tar.bz2 "https://github.com/HandBrake/HandBrake/releases/download/$HANDBRAKE_VERSION/HandBrake-$HANDBRAKE_VERSION-source.tar.bz2"

# https://handbrake.fr/openpgp.php or https://github.com/HandBrake/HandBrake/wiki/OpenPGP
GNUPGHOME="$(mktemp -d)" && export GNUPGHOME
gpg --batch --keyserver keyserver.ubuntu.com --recv-keys '1629 C061 B3DD E7EB 4AE3  4B81 021D B8B4 4E4A 8645'; \
gpg --batch --verify handbrake.tar.bz2.sig handbrake.tar.bz2; \
rm -rf "$GNUPGHOME" handbrake.tar.bz2.sig
mkdir -p /tmp/handbrake
tar --extract \
	--file handbrake.tar.bz2 \
	--directory /tmp/handbrake \
	--strip-components 1 \
	"HandBrake-$HANDBRAKE_VERSION"
rm handbrake.tar.bz2

# libdovi (Dolby Vision) support
curl https://sh.rustup.rs -sSf | sh -s -- --default-toolchain nightly -y
source "$HOME/.cargo/env"
cargo install cargo-c
rustup target add x86_64-pc-windows-gnu

# build
cd /tmp/handbrake
nproc="$(nproc)"
./configure --disable-gtk --enable-qsv --enable-vce --enable-libdovi --launch-jobs="$nproc" --launch
make -C build -j "$nproc"
make -C build install
cp /usr/local/bin/HandBrakeCLI /usr/bin/HandBrakeCLI
cd /

# cleanup
rustup self uninstall -y
rm -rf "$HOME/.cargo/"
rm -rf /root/.rustup
rm -rf /tmp/handbrake
