#!/bin/bash
echo Input ISO Name Without .ISO:
read isofolder
isoname=$isofolder.ISO
echo Gonig to be converting $isoname
sleep 2
mkdir ./$isofolder
rawout=$(HandBrakeCLI -i ./$isoname -t 0 2>&1 >/dev/null)
#read handbrake's stderr into variable

count=$(echo $rawout | grep -Eao "\\+ title [0-9]+:" | wc -l)
#parse the variable using grep to get the count

for i in $(seq $count)
do
	    HandBrakeCLI --input ./$isoname --title $i --preset Normal --output ./$isof$
done
