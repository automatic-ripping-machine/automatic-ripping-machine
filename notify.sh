#!/bin/bash

# shellcheck source=config
# shellcheck disable=SC1091
source "$ARM_CONFIG"
MSG=$1

{
#Notification via pushbullet
#Trigger onl if variable is set
if [ -z "$PB_KEY" ]; then
	echo "Pushbullet notifications not enabled" >> "$LOG"
else
	echo "Sending Pushbullet notification" >> "$LOG"
	curl -s -u "$PB_KEY": https://api.pushbullet.com/v2/pushes -d type=note -d title="Alert" -d body="$MSG"
	echo "Pushbullet notification sent" >> "$LOG"
fi

#Notification via IFTTT
#Trigger only if variable is set
if [ -z "$IFTTT_KEY" ]; then
	echo "IFTTT notifications not enabled" >> "$LOG"
else
	echo "Sending IFTTT notification" >> "$LOG"
	curl -s -X POST -H "Content-Type: application/json" -d '{"value1":"'"$MSG"'"}' https://maker.ifttt.com/trigger/"$IFTTT_EVENT"/with/key/"$IFTTT_KEY"
	printf "\nIFTTT notification sent" >> "$LOG"
fi

#Notification via Pushover
#Trigger onl if variable is set
if [ -z "$PO_USER_KEY" ]; then
        echo "Pusover notifications not enabled" >> "$LOG"
else
        echo "Sending Pushover notification" >> "$LOG"
        curl -s --form-string "token=$PO_APP_KEY"  --form-string "user=$PO_USER_KEY" --form-string "message=$MSG" https://api.pushover.net/1/messages.json
        echo "Pushover notification sent" >> "$LOG"
fi

#Notification via E-Mail - Note this requires an already functional PostFix/Mutt installation
#Trigger onl if variable is set
if [ -z "$EMAIL_NOTIFY" ]; then
        echo "EMail notifications not enabled" >> "$LOG"
else
        echo "Sending EMail notification" >> "$LOG"
        echo "${MSG}" | mutt -s "ARM Alert from `hostname`" ${EMAIL_NOTIFY}
	echo "EMail notification sent" >> "$LOG"
fi


} >> "$LOG"

