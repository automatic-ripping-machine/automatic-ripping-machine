#!/bin/bash

#newkey=T-_r0kX0iTg1cpZPCL1sofKlaPwiCGGg_PkNKUwSxCy4SlbHfDSF9CSNE5MGRTRh9BPq
newkey=$(curl -A "Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_3_3 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8J2 Safari/6533.18.5" https://cable.ayra.ch/makemkv/api.php?raw)
newkey="app_Key=\"$newkey\""
settingsfile='/home/arm/.MakeMKV/settings.conf'
#echo $newkey
if grep -q app_Key $settingsfile; then
	echo found correct line.
	sed -i "s/app_Key.*/$newkey/" $settingsfile
else
	echo could not find line, dump at the bottom.
	echo $newkey >> $settingsfile
fi
cat $settingsfile
