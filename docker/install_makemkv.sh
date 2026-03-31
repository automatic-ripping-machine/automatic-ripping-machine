#!/bin/bash

# Based on https://github.com/tianon/dockerfiles/blob/master/makemkv/Dockerfile
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

set -ex

MAKEMKV_VERSION="${1:?Usage: install_makemkv.sh <version>}"

wget -O 'sha256sums.txt.sig' "https://www.makemkv.com/download/makemkv-sha-${MAKEMKV_VERSION}.txt"
GNUPGHOME="$(mktemp -d)" && export GNUPGHOME
gpg --batch --keyserver keyserver.ubuntu.com --recv-keys 2ECF23305F1FC0B32001673394E3083A18042697
gpg --batch --decrypt --output sha256sums.txt sha256sums.txt.sig
gpgconf --kill all
rm -rf "$GNUPGHOME" sha256sums.txt.sig

export PREFIX='/usr/local'
for ball in makemkv-oss makemkv-bin; do
    wget -O "$ball.tgz" "https://www.makemkv.com/download/${ball}-${MAKEMKV_VERSION}.tar.gz"
    sha256="$(grep "  $ball-${MAKEMKV_VERSION}[.]tar[.]gz\$" sha256sums.txt)"
    sha256="${sha256%% *}"
    [ -n "$sha256" ]
    echo "$sha256 *$ball.tgz" | sha256sum -c -
    mkdir -p "$ball"
    tar -xf "$ball.tgz" -C "$ball" --strip-components=1
    rm "$ball.tgz"
    cd "$ball"
    if [ -f configure ]; then
        ./configure --prefix="$PREFIX"
    else
        mkdir -p tmp && touch tmp/eula_accepted
    fi
    make -j "$(nproc)" PREFIX="$PREFIX"
    make install PREFIX="$PREFIX"
    cd ..
    rm -r "$ball"
done

rm sha256sums.txt
