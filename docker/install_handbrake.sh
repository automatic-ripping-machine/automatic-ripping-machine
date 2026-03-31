#!/bin/bash

# Based on https://github.com/tianon/dockerfiles/blob/master/handbrake/Dockerfile
# via https://github.com/automatic-ripping-machine/arm-dependencies
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

set -eux

HANDBRAKE_VERSION="$(cat /tmp/VERSION_HANDBRAKE)"
echo "Building HandBrake $HANDBRAKE_VERSION"

wget -O handbrake.tar.bz2 \
    "https://github.com/HandBrake/HandBrake/releases/download/$HANDBRAKE_VERSION/HandBrake-$HANDBRAKE_VERSION-source.tar.bz2"
mkdir -p /tmp/handbrake
tar --extract --file handbrake.tar.bz2 --directory /tmp/handbrake \
    --strip-components 1 "HandBrake-$HANDBRAKE_VERSION"
rm handbrake.tar.bz2

# Dolby Vision support (cargo-c needed to build libdovi)
cargo install cargo-c

cd /tmp/handbrake
nproc="$(nproc)"
./configure --disable-gtk --enable-qsv --enable-vce --enable-libdovi \
    --launch-jobs="$nproc" --launch
make -C build -j "$nproc"
make -C build install

# Cleanup
rm -rf "$HOME/.cargo/" /tmp/handbrake
