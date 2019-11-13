#!/bin/bash

## original usage
#/opt/arm/scripts/arm_wrapper.sh sr0

disc="/dev/sr0"
while getopts ":hf:" opt; do
	case $opt in
		h)
			echo "usage: -h: This help menu"
			echo "       -f: /path/to/file.
otherwise default to /dev/sr0"
			echo "       -e: noeject"
			exit 0
			;;
		f)
			echo "-f $OPTARG"
			disc=$OPTARG
			;;
		e)
			echo "-e noeject"
			eject=false
			;;
		\?)
			echo "invalid option"
			exit 1
			;;
	esac
done

/usr/bin/python3 /opt/arm/arm/main.py -d "$disc"
