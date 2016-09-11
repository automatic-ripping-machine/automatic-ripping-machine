#!/bin/bash

source /opt/arm/config
MSG=$1

{
#Notification via pushbullet
#Trigger onl if variable is set
if [ -z "$PB_KEY" ]; then
	echo "Pushbullet notifications not enabled" >> $LOG
else
	curl -s -u $PB_KEY: https://api.pushbullet.com/v2/pushes -d type=note -d title="Alert" -d body="$MSG"
	echo "Pushbullet notification sent" >> $LOG
fi

#Notification via IFTTT
#Trigger only if variable is set
if [ -z "$IFTTT_KEY" ]; then
	echo "IFTTT notifications not enabled" >> $LOG
else
	curl -s -X POST -H "Content-Type: application/json" -d '{"value1":"'"$MSG"'"}' https://maker.ifttt.com/trigger/${IFTTT_EVENT}/with/key/${IFTTT_KEY}
	printf "\nIFTTT notification sent" >> $LOG
fi

} >> $LOG

