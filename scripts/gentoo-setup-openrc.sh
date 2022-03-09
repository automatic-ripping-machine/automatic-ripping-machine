#!/bin/bash

###################################################################################################
# Setup automatic-ripping-machine (ARM) for Gentoo systems running OpenRC.
###################################################################################################

# Exit on error.
set -e

RED='\033[1;31m'
NC='\033[0m' # No Color

echo -e "${RED}Adding arm user${NC}"
if [ ! $(getent group arm) ]; then
	groupadd arm
fi

if [ ! $(getent passwd arm) ]; then
	useradd -m arm -g arm -G cdrom,video,audio
	# If a password was specified use that, otherwise prompt
	if [ -n "$1" ]; then
		echo "$1" | passwd --stdin arm
	else
		passwd arm
	fi
fi

# Install, but don't reinstall, packages or add them to world
################################################################################

function mergeifneeded() {
	if [ ! -e /usr/bin/eix ]; then
		emerge -a app-portage/eix
		eix-update
	fi

	installed=$(eix -I $1) || true
	if [ "$installed" = "No matches found" ]; then
		# Not installed at all
		emerge -a $1
	else
		if ! grep -qE "^${1}$" /var/lib/portage/world; then
			# installed but not in world, add to world
			emerge --noreplace $1
		fi
	fi
}

echo
echo -e "${RED}Installing Packages${NC}"
echo This script was developed for OpenRC based Gentoo Systems
echo
echo The "default/linux/amd64/17.1/desktop/plasma (stable)" profile
echo was selected and the kde-plasma/plasma-meta package was installed.
echo If your profile or desktop environment differ you may need to
echo adjust this script.
echo
echo This script will stop for any issues such as licenses or use flags.
echo Resolve the issue and rerun the script.
echo How to resolve the issue is beyond the scope of this script.
echo
echo To watch emerge progress in another window use:
echo '    watch -c "genlop -c"'
echo
echo You may need to emerge genlop first.
echo

#provides equery for later use
mergeifneeded app-portage/gentoolkit

#non-Gentoo specific packages
mergeifneeded dev-vcs/git
mergeifneeded media-video/makemkv
mergeifneeded media-video/ffmpeg
mergeifneeded media-video/handbrake
mergeifneeded media-libs/libdvdcss
mergeifneeded media-sound/abcde
mergeifneeded media-libs/flac
mergeifneeded media-gfx/imagemagick
mergeifneeded media-libs/glyr
mergeifneeded media-sound/cdparanoia
mergeifneeded sys-process/at
mergeifneeded dev-python/pip
mergeifneeded media-video/lsdvd

#java jre
installed=$(eix -I virtual/jre) || true
if [ "$installed" = "No matches found" ]; then
	echo
	echo -e "${RED}Configuring a Jave Runtime${NC}"
	echo This script will merge virtual/jre but the actual JRE installed
	echo will vary based upon your USE flags and configuration.
	echo
	echo Because of this it is not possible to automatically configure the
	echo merged package to be headless. If you would like your installed
	echo JRE running in a headless mode you should add USE flags to the
	echo package.use file in /etc/portage for the JRE being merged.
	echo
	echo '   dev-java/jre-package    headless-awt -alsa -cups'
	echo
	echo Replacing jre-package with the name of your actual JRE.
	echo
	echo The next command to run will show you which JRE will be merged.
	echo You can enter no when prompted to stop the installation and
	echo update your package.use file as needed.
	echo
	read -n1 -s -r -p $'Press Enter to continue...\n' key
	emerge -a virtual/jre
fi

# Handbrake 1.3 is not compatible with FFMpeg 4.4
################################################################################

version_greater_equal() {
    printf '%s\n%s\n' "$2" "$1" | sort --check=quiet --version-sort
}

hb_ver=$(eix -I handbrake | grep "Installed versions:" | tr -s " " | cut -d " " -f 4 | cut -d "-" -f 1)
ff_ver=$(eix -I ffmpeg    | grep "Installed versions:" | tr -s " " | cut -d " " -f 4 | cut -d "-" -f 1)

echo Handbrake: $hb_ver
echo FFMpeg:    $ff_ver
if ! version_greater_equal $hb_ver 1.4 && version_greater_equal $ff_ver 4.4 ; then
	echo
	echo -e "${RED}!!! Warning !!!${NC}"
	echo
	echo Versions of Handbrake prior to 1.4 do not officially support
	echo FFmpeg 4.4. Common issues include the inability to properly
	echo transcode audio resulting in silent media files.
	echo
	echo You may need to mask FFmpeg 4.4 until Handbrake 1.4 is available.
	echo
	read -n1 -s -r -p $'Press Enter to continue...\n' key
fi

# Git Clone the ARM project
################################################################################

echo
echo -e "${RED}Installing ARM:Automatic Ripping Machine${NC}"
cd /opt

if [ ! -d arm ]; then
	mkdir -p /opt/arm
fi

chown arm:arm arm
chmod 775 arm

if [ -d /opt/arm/.git ]; then
	cd /opt/arm
	git fetch
	cd /opt
else
	git clone https://github.com/1337-server/automatic-ripping-machine.git arm

	###stock
	#git clone https://github.com/automatic-ripping-machine/automatic-ripping-machine.git arm
fi

chown -R arm:arm arm
cd arm

# Try to convert requirements.txt into ebuilds, otherwise install for arm user
################################################################################

echo
echo -e "${RED}Installing Required Python Libraries${NC}"
for line in $(cat requirements.txt) ; do

	reqpkg=$(echo $line | cut -d '>' -f 1 | tr '[:upper:]' '[:lower:]')

	#TODO: Probably not completely safe to check for repo directory

	if [ -d /var/db/repos/gentoo/dev-python/$reqpkg ]; then
		reqpkg="dev-python/${reqpkg}"
		mergeifneeded $reqpkg
	else
		if [ -d /var/db/repos/gentoo/dev-python/python-$reqpkg ]; then
			reqpkg="dev-python/python-${reqpkg}"
			mergeifneeded $reqpkg
		else
			/bin/su -l -c "/usr/bin/pip install --user ${line}" -s /bin/bash arm
		fi
	fi

done

# Link and Copy
################################################################################

ln -s /opt/arm/setup/51-automedia.rules /lib/udev/rules.d/
ln -s /opt/arm/setup/.abcde.conf /home/arm/
cp docs/arm.yaml.sample arm.yaml
mkdir -p /etc/arm/
ln -s /opt/arm/arm.yaml /etc/arm/
chmod +x /opt/arm/scripts/arm_wrapper.sh
chmod +x /opt/arm/scripts/update_key.sh

# System Files
################################################################################

echo
echo -e "${RED}Adding fstab entry and creating mount points${NC}"
for dev in /dev/sr?; do
   #echo -e "\n${dev}  /mnt${dev}  udf,iso9660  users,noauto,exec,utf8  0  0 \n" >> /etc/fstab
   mkdir -p /mnt$dev
done

##### Add sysctl.d rule to prevent auto-unejecting cd tray
cat > /etc/sysctl.d/arm-uneject-fix.conf <<-EOM
# Fix issue with DVD tray being autoclosed after rip is complete

dev.cdrom.autoclose=0
EOM

##### Add syslog rule to route all ARM system logs to /var/log/arm.log

# TODO: Untested, not installed on dev system

if [ -d /etc/rsyslog.d ]; then
	cat > /etc/rsyslog.d/arm.conf <<-EOM
:programname, isequal, "ARM" /var/log/arm.log
EOM
	/etc/init.d/rsyslog restart
fi

# TODO: Doesn't seem to be working

if ! grep -qE "^ARM :$" /etc/metalog.conf; then
	echo '' >> /etc/metalog.conf
	echo 'ARM :' >> /etc/metalog.conf
	echo '    regex  = "^arm"' >> /etc/metalog.conf
	echo '    logdir = "/var/log/arm"' >> /etc/metalog.conf
	echo '    break  = 1' >> /etc/metalog.conf
	echo '' >> /etc/metalog.conf

	/etc/init.d/metalog restart
fi

##### Run the ARM UI as a service.
echo -e "${RED}Installing OpenRC ARM service${NC}"
cat > /etc/init.d/armui <<- EOM
#!/sbin/openrc-run

depend() {
        need net
}

start() {
        /bin/su -l -c "/usr/bin/python3 /opt/arm/arm/runui.py 2>&1 >/dev/null &" -s /bin/bash arm
}

stop() {
        pkill -u arm -9 -f "runui.py"
}
EOM

##### Add the armui and atd service to the default runlevel
chmod +x /etc/init.d/armui
/sbin/rc-update add armui default
/etc/init.d/armui start

/sbin/rc-update add atd default
/etc/init.d/atd start

#advise to reboot
echo
echo -e "${RED}We recommend rebooting your system at this time.${NC}"
echo
