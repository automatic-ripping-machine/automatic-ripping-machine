#!/bin/bash

DEVNAME=$1

sleep 5 # allow the system enough time to load disc information such as title

echo "[ARM] Starting ARM on ${DEVNAME}" | logger -t ARM -s
/bin/su -l -c "echo /usr/bin/python3 /opt/arm/arm/ripper/main.py -d ${DEVNAME} | at now" -s /bin/bash arm

# Check to see if the admin page is running, if not, start it
if pgrep -f "runui.py" > /dev/null
then
        echo "[ARM] ARM Webgui running. " | logger -t ARM -s
else
        echo "[ARM] ARM Webgui not running; starting it "| logger -t ARM -s
        /bin/su -l -c "/usr/bin/python3 /opt/arm/arm/runui.py  " -s /bin/bash arm
        # Try the below line if you want it to log to your log file of choice
        #/bin/su -l -c "/usr/bin/python3 /opt/arm/arm/runui.py  &> [pathtologDir]/WebUI.log" -s /bin/bash arm
fi
