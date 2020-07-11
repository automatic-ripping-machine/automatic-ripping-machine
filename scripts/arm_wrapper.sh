#!/bin/bash

DEVNAME=$1

# Check to see if the admin page is running, if not, start it
if pgrep -f "runui.py" > /dev/null
then
        echo "ARM Webgui running  on " | logger -t ARM
else
        echo "ARM Webgui not running  on starting it "| logger -t ARM
        /bin/su -l -c "/usr/bin/python3 /opt/arm/arm/runui.py  " -s /bin/bash arm
        # Try the below line if you want it to log to your log file of choice
        #/bin/su -l -c "/usr/bin/python3 /opt/arm/arm/runui.py  &> [pathtologDir]/WebUI.log" -s /bin/bash arm
fi

echo "Starting ARM on ${DEVNAME}" | logger -t ARM
/bin/su -l -c "echo /usr/bin/python3 /opt/arm/arm/main.py -d ${DEVNAME} | at now" -s /bin/bash arm
