# Collection of utility functions

import os
import sys
import logging
import fcntl
import subprocess
import shutil
import requests
import time
import apprise
## Added from pull 366
import datetime  # noqa: E402
import psutil  # noqa E402

# from arm.config.config import cfg
from arm.ui import app, db # noqa E402
from arm.models.models import Track  # noqa: E402


def notify(job, title, body):
    # Send notificaions
    # title = title for notification
    # body = body of the notification

    ## Pushbullet
    ## pbul://{accesstoken}
    if job.config.PB_KEY != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            # A sample pushbullet notification
            apobj.add('pbul://' + str(job.config.PB_KEY))
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending Pushbullet apprise notification.  Continueing processing...")
    ## boxcar
    ## boxcar://{access_key}/{secret_key}
    if job.config.BOXCAR_KEY != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            # A sample pushbullet notification
            apobj.add('boxcar://' + str(job.config.BOXCAR_KEY) + "/" + str(job.config.BOXCAR_SECRET))

            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending boxcar apprise notification.  Continueing processing...")
    ## discord
    ## discord://{WebhookID}/{WebhookToken}/
    if job.config.DISCORD_WEBHOOK_ID != "":
        ## TODO: add userid to this and config
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            # A sample pushbullet notification
            apobj.add('discord://' + str(job.config.DISCORD_WEBHOOK_ID) + "/" + str(job.config.DISCORD_TOKEN))

            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending discord apprise notification.  Continueing processing...")
    ## Faast
    ## faast://{authorizationtoken}
    if job.config.FAAST_TOKEN != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            # A sample pushbullet notification
            apobj.add('faast://' + str(job.config.FAAST_TOKEN))

            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending faast apprise notification.  Continueing processing...")
    ## FLOCK
    ## flock://{token}/
    if job.config.FLOCK_TOKEN != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            # A sample pushbullet notification
            apobj.add('flock://' + str(job.config.FLOCK_TOKEN))

            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending flock apprise notification.  Continueing processing...")
    ## GITTER
    ## gitter: // {token} / {room} /
    if job.config.GITTER_TOKEN != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            # A sample pushbullet notification
            apobj.add('gitter://' + str(job.config.GITTER_TOKEN) + "/" + str(job.config.GITTER_ROOM))

            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending gitter apprise notification.  Continueing processing...")
    ## Gotify
    ## gotify://{hostname}/{token}
    if job.config.GOTIFY_TOKEN != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            # A sample pushbullet notification
            apobj.add('gotify://' + str(job.config.GOTIFY_HOST) + "/" + str(job.config.GOTIFY_TOKEN))

            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending gitter apprise notification.  Continueing processing...")
    ## Growl
    ## growl://{hostname} || growl://{password}@{hostname}
    if job.config.GROWL_HOST != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            ## Check if we have a pass, use it if we do
            if job.config.GROWL_PASS != "":
                # A sample pushbullet notification
                apobj.add('growl://' + str(job.config.GROWL_PASS) + "@" + str(job.config.GROWL_HOST))
            else:
                # A sample pushbullet notification
                apobj.add('growl://' + str(job.config.GROWL_HOST))
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending growl apprise notification.  Continueing processing...")
    ## IFTTT
    ## ifttt://{WebhookID}@{Event}/
    if job.config.IFTTT_KEY != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            # A sample pushbullet notification
            apobj.add('ifttt://' + str(job.config.IFTTT_KEY) + "@" + str(job.config.IFTTT_EVENT))

            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending IFTTT apprise notification.  Continueing processing...")
    ## JOIN
    ## join://{apikey}/ ||  join://{apikey}/{device_id}
    if job.config.JOIN_API != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            ## Check if we have a pass, use it if we do
            if job.config.JOIN_DEVICE != "":
                # A sample pushbullet notification
                apobj.add('join://' + str(job.config.JOIN_API) + "/" + str(job.config.JOIN_DEVICE))
            else:
                # A sample pushbullet notification
                apobj.add('join://' + str(job.config.JOIN_API))
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending growl apprise notification.  Continueing processing...")
    ## Kodi
    ## kodi://{hostname}:{port} || kodi: // {userid}: {password} @ {hostname}:{port}
    if job.config.KODI_HOST != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            # check if we have login details, if so use them
            if job.config.KODI_USER != "":
                apobj.add('kodi://' + str(job.config.KODI_USER) + ":" + str(job.config.KODI_PASS) + "@"+ str(job.config.KODI_HOST) + ":" + str(job.config.KODI_PORT))
            else:
                if job.config.KODI_PORT != "":
                    ## we need to check if they are using secure or this will fail
                    if job.config.KODI_PORT == "443":
                        apobj.add('kodis://' + str(job.config.KODI_HOST) + ":" + str(job.config.KODI_PORT))
                    else:
                        apobj.add('kodi://' + str(job.config.KODI_HOST) + ":" + str(job.config.KODI_PORT))
                else:
                    apobj.add('kodi://' + str(job.config.KODI_HOST))
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending KODI apprise notification.  Continueing processing...")
    ## KUMULOS
    if job.config.KUMULOS_API != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            # A sample pushbullet notification
            apobj.add('kumulos://' + str(job.config.KUMULOS_API) + "/" + str(job.config.KUMULOS_SERVERKEY))

            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending KUMULOS apprise notification.  Continueing processing...")
    ## LEMETRIC
    if job.config.LAMETRIC_MODE != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()

            ## find the correct mode
            if job.config.LAMETRIC_MODE == "device":
                apobj.add('lametric://' + str(job.config.LAMETRIC_API) + "@" + str(job.config.LAMETRIC_HOST))
            elif job.config.LAMETRIC_MODE == "cloud":
                apobj.add('lametric://' + str(job.config.LAMETRIC_APP_ID) + "@" + str(job.config.LAMETRIC_TOKEN))
            else:
                logging.error("LAMETRIC apprise LAMETRIC_MODE not set")
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending LAMETRIC apprise notification.  Continueing processing...")
    ## MAILGUN
    if job.config.MAILGUN_DOMAIN != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            # A sample pushbullet notification
            apobj.add('mailgun://' + str(job.config.MAILGUN_USER) + "@" + str(job.config.MAILGUN_DOMAIN) + "/"+ str(job.config.MAILGUN_APIKEY))

            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending mailgun apprise notification.  Continueing processing...")
    ## MATRIX
    if job.config.MATRIX_HOST != "" or job.config.MATRIX_TOKEN != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            if job.config.MATRIX_HOST != "":
                apobj.add('matrixs://' + str(job.config.MATRIX_USER) + ":" + str(job.config.MATRIX_PASS) + "@"+ str(job.config.MATRIX_HOST)) # + "/#general/#apprise")
            else:
                apobj.add('matrix://' + str(job.config.MATRIX_TOKEN) )
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending Matrix apprise notification.  Continueing processing...")
    ## Microsoft teams
    if job.config.MSTEAMS_TOKENA != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()

            # msteams://{tokenA}/{tokenB}/{tokenC}/
            apobj.add('msteams://' + str(job.config.MSTEAMS_TOKENA) + "/" + str(job.config.MSTEAMS_TOKENB) + "/"+ str(job.config.MSTEAMS_TOKENC) + "/")

            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending Microsoft teams apprise notification.  Continueing processing...")
    ## Nextcloud
    if job.config.NEXTCLOUD_HOST != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()

            apobj.add('nclouds://' + str(job.config.NEXTCLOUD_ADMINUSER) + ":" + str(job.config.NEXTCLOUD_ADMINPASS) + "@"+ str(job.config.NEXTCLOUD_HOST) + "/"+ str(job.config.NEXTCLOUD_NOTIFY_USER))

            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending nextcloud apprise notification.  Continueing processing...")
    ## Notica
    if job.config.NOTICA_TOKEN != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()

            apobj.add('notica://' + str(job.config.NOTICA_TOKEN) )

            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending notica apprise notification.  Continueing processing...")
    ## Notifico
    if job.config.NOTIFICO_PROJECTID != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()

            apobj.add('notica://' + str(job.config.NOTIFICO_PROJECTID) + "/" + str(job.config.NOTIFICO_MESSAGEHOOK) )

            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending notifico apprise notification.  continuing  processing...")
    ## Office365
    if job.config.OFFICE365_TENANTID != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()

            #o365://{tenant_id}:{account_email}/{client_id}/{client_secret}/
            # TODO: we might need to escape/encode the client_secret
            # Replace ? with %3F and  @ with %40
            apobj.add('o365://' + str(job.config.OFFICE365_TENANTID) + ":" + str(job.config.OFFICE365_ACCOUNTEMAIL) + "/" +str(job.config.OFFICE365_CLIENT_ID) + "/" + str(job.config.OFFICE365_CLIENT_SECRET))

            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending Office365 apprise notification.  continuing processing...")
    ## Popcorn
    if job.config.POPCORN_API != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            if job.config.POPCORN_EMAIL != "":
                apobj.add('popcorn://' + str(job.config.POPCORN_API) + "/" + str(job.config.POPCORN_EMAIL) )
            if job.config.POPCORN_PHONENO != "":
                apobj.add('popcorn://' + str(job.config.POPCORN_API) + "/" + str(job.config.POPCORN_PHONENO))
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending popcorn apprise notification.  Continueing processing...")
    ## PROWL
    if job.config.PROWL_API != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            if job.config.PROWL_PROVIDERKEY != "":
                apobj.add('prowl://' + str(job.config.PROWL_API) + "/" + str(job.config.PROWL_PROVIDERKEY) )
            else:
                apobj.add('prowl://' + str(job.config.PROWL_API) )
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending notifico apprise notification.  continuing  processing...")
    ## Pushjet
    ## project is dead not worth coding fully
    if job.config.PUSHJET_HOST != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()

            apobj.add('pjet://' + str(job.config.PUSHJET_HOST) )
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending pushjet apprise notification.  continuing  processing...")
    ## techulus push
    if job.config.PUSH_API != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()

            apobj.add('push://' + str(job.config.PUSH_API) )
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending techulus push apprise notification.  continuing  processing...")
    ## PUSHED
    if job.config.PUSHED_APP_KEY != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()

            apobj.add('pushed://' + str(job.config.PUSHED_APP_KEY) + "/" +  str(job.config.PUSHED_APP_SECRET) )
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending PUSHED apprise notification.  continuing  processing...")
    ## PUSHOVER
    if job.config.PO_USER_KEY != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()

            apobj.add('pover://' + str(job.config.PO_USER_KEY) + "@" +  str(job.config.PO_APP_KEY) )
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending PUSHOVER apprise notification.  continuing  processing...")
    ## PUSHSAFER
    if job.config.PUSHSAFER_KEY != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()

            apobj.add('psafers://' + str(job.config.PUSHSAFER_KEY) )
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending pushsafer apprise notification.  continuing  processing...")
    ## ROCKETCHAT
    ## rocket://{webhook}@{hostname}/{@user}
    if job.config.ROCKETCHAT_HOST != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            ## TODO: Add checks for webhook or default modes
            ## for now only the webhook will work
            apobj.add('rocket://' + str(job.config.ROCKETCHAT_WEBHOOK) + "@" + str(job.config.ROCKETCHAT_HOST) )
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending rocketchat apprise notification.  continuing  processing...")
    ## ryver
    ## ryver://{organization}/{token}/
    if job.config.RYVER_ORG != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            ## TODO: Add checks for webhook or default modes
            ## for now only the webhook will work
            apobj.add('ryver://' + str(job.config.RYVER_ORG) + "/" + str(job.config.RYVER_TOKEN) + "/")
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending RYVER apprise notification.  continuing  processing...")
    ## Sendgrid
    ## sendgrid://{apikey}:{from_email}
    if job.config.SENDGRID_API != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            ## TODO: Add tomail
            apobj.add('sendgrid://' + str(job.config.SENDGRID_API) + ":" + str(job.config.SENDGRID_FROMMAIL))
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending sendgrid apprise notification.  continuing  processing...")
    ## simplepush
    ## spush://{apikey}/
    if job.config.SIMPLEPUSH_API != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            apobj.add('spush://' + str(job.config.SIMPLEPUSH_API) )
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending simplepush apprise notification.  continuing  processing...")
    ## slacks
    ## slack://{tokenA}/{tokenB}/{tokenC}
    if job.config.SLACK_TOKENA != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            apobj.add('slack://' + str(job.config.SLACK_TOKENA) + "/" + str(job.config.SLACK_TOKENB) + "/"  + str(job.config.SLACK_TOKENC) + "/" + str(job.config.SLACK_CHANNEL))
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending slacks apprise notification.  continuing  processing...")
    ## SPARKPOST
    ## sparkpost://{user}@{domain}/{apikey}/ || sparkpost://{user}@{domain}/{apikey}/{email}/
    if job.config.SPARKPOST_API != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            apobj.add('sparkpost://' + str(job.config.SPARKPOST_USER) + "@" + str(job.config.SPARKPOST_HOST) + "/"  + str(job.config.SPARKPOST_API) + "/" + str(job.config.SPARKPOST_EMAIL))
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending SparkPost apprise notification.  continuing  processing...")
    ## spontit
    ## spontit://{user}@{apikey}
    if job.config.SPONTIT_API != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            apobj.add('spontit://' + str(job.config.SPONTIT_USER_ID) + "@" + str(job.config.SPONTIT_API))
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending Spontit apprise notification.  continuing  processing...")
    ## Telegram
    ## tgram://{bot_token}/{chat_id}/ || tgram://{bot_token}/
    if job.config.TELEGRAM_BOT_TOKEN != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            apobj.add('tgram://' + str(job.config.TELEGRAM_BOT_TOKEN) + "/" + str(job.config.TELEGRAM_CHAT_ID))
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending Telegram apprise notification.  continuing  processing...")
    ## Twist
    ## twist://{email}/{password} || twist://{password}:{email}
    if job.config.TWIST_EMAIL != "":
        try:
            # Create an Apprise instance
            ## TODO: add channel var and check if its blank
            apobj = apprise.Apprise()
            apobj.add('twist://' + str(job.config.TWIST_EMAIL) + "/" + str(job.config.TWIST_PASS))
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending Twist apprise notification.  continuing  processing...")
    ## XBMC
    ## xbmc://{userid}:{password}@{hostname}:{port} ||  xbmc://{hostname}:{port}
    if job.config.XBMC_HOST != "":
        try:
            # Create an Apprise instance
            ## TODO: add channel var and check if its blank
            apobj = apprise.Apprise()
            ## if we get user we use the username and pass
            if job.config.XBMC_USER != "":
                apobj.add('xbmc://' + str(job.config.XBMC_USER) + ":" + str(job.config.XBMC_PASS) + "@" + str(job.config.XBMC_HOST) + ":" + str(job.config.XBMC_PORT))
            else:
                apobj.add('xbmc://' + str(job.config.XBMC_HOST) + ":" + str(job.config.XBMC_PORT))
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending XBMC apprise notification.  continuing  processing...")
    ## XMPP
    ## xmpp://{password}@{hostname}:{port} || xmpps://{userid}:{password}@{hostname}
    if job.config.XMPP_HOST != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()
            ## Is the user var filled
            if job.config.XMPP_USER != "":
                #xmpps://{userid}:{password}@{hostname}
                apobj.add('xmpps://' + str(job.config.XMPP_USER) + ":" + str(job.config.XMPP_PASS) + "@" + str(job.config.XMPP_HOST) )
            else:
                #xmpp: // {password} @ {hostname}: {port}
                apobj.add('xmpp://' + str(job.config.XMPP_PASS) + "@" + str(job.config.XMPP_HOST))
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending XMPP apprise notification.  continuing  processing...")
    ## Webex teams
    ## wxteams://{token}/
    if job.config.WEBEX_TEAMS_TOKEN != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()

            apobj.add('wxteams://' + str(job.config.WEBEX_TEAMS_TOKEN) )
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending Webex teams apprise notification.  continuing  processing...")
    ## Zulip
    ## zulip://{botname}@{organization}/{token}/
    if job.config.ZILUP_CHAT_TOKEN != "":
        try:
            # Create an Apprise instance
            apobj = apprise.Apprise()

            apobj.add('zulip://' + str(job.config.ZILUP_CHAT_BOTNAME) + "@" +  str(job.config.ZILUP_CHAT_ORG) + "/" + str(job.config.ZILUP_CHAT_TOKEN))
            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body,
                title=title,
            )
        except:  # noqa: E722
            logging.error("Failed sending Zulip apprise notification.  continuing  processing...")



def scan_emby(job):
    """Trigger a media scan on Emby"""

    if job.config.EMBY_REFRESH:
        logging.info("Sending Emby library scan request")
        url = "http://" + job.config.EMBY_SERVER + ":" + job.config.EMBY_PORT + "/Library/Refresh?api_key=" + job.config.EMBY_API_KEY
        try:
            req = requests.post(url)
            if req.status_code > 299:
                req.raise_for_status()
            logging.info("Emby Library Scan request successful")
        except requests.exceptions.HTTPError:
            logging.error("Emby Library Scan request failed with status code: " + str(req.status_code))
    else:
        logging.info("EMBY_REFRESH config parameter is false.  Skipping emby scan.")

## New function from pull 366
## Adds max number of transcodes
## Need to add user config variables
def SleepCheckProcess(ProcessStr, Proc_Count):

    if Proc_Count != 0:
        Loop_Count = Proc_Count + 1
        logging.debug("Loop_Count " + str(Loop_Count))
        logging.info("Starting A sleep check of " + str(ProcessStr))
        while Loop_Count >= Proc_Count:
            Loop_Count = sum(1 for proc in psutil.process_iter() if proc.name() == ProcessStr)
            logging.debug("Number of Processes running is:" + str(Loop_Count) + " going to waiting 12 seconds.")
            time.sleep(10)
    else:
        logging.info("Number of processes to count is: " + str(Proc_Count))

def move_files(basepath, filename, job, ismainfeature=False):
    """Move files into final media directory\n
    basepath = path to source directory\n
    filename = name of file to be moved\n
    job = instance of Job class\n
    ismainfeature = True/False"""

    logging.debug("Moving files: " + str(job))

    if job.title_manual:
        # logging.info("Found new title: " + job.new_title + " (" + str(job.new_year) + ")")
        # videotitle = job.new_title + " (" + str(job.new_year) + ")"
        hasnicetitle = True
    else:
        hasnicetitle = job.hasnicetitle

    videotitle = job.title + " (" + str(job.year) + ")"

    logging.debug("Arguments: " + basepath + " : " + filename + " : " + str(hasnicetitle) + " : " + videotitle + " : " + str(ismainfeature))

    if hasnicetitle:
        m_path = os.path.join(job.config.MEDIA_DIR + videotitle)

        if not os.path.exists(m_path):
            logging.info("Creating base title directory: " + m_path)
            os.makedirs(m_path)

        if ismainfeature is True:
            logging.info("Track is the Main Title.  Moving '" + filename + "' to " + m_path)

            m_file = os.path.join(m_path, videotitle + "." + job.config.DEST_EXT)
            if not os.path.isfile(m_file):
                try:
                    shutil.move(os.path.join(basepath, filename), m_file)
                except shutil.Error:
                    logging.error("Unable to move '" + filename + "' to " + m_path)
            else:
                logging.info("File: " + m_file + " already exists.  Not moving.")
        else:
            e_path = os.path.join(m_path, job.config.EXTRAS_SUB)

            if not os.path.exists(e_path):
                logging.info("Creating extras directory " + e_path)
                os.makedirs(e_path)

            logging.info("Moving '" + filename + "' to " + e_path)

            e_file = os.path.join(e_path, videotitle + "." + job.config.DEST_EXT)
            if not os.path.isfile(e_file):
                try:
                    shutil.move(os.path.join(basepath, filename), os.path.join(e_path, filename))
                except shutil.Error:
                    logging.error("Unable to move '" + filename + "' to " + e_path)
            else:
                logging.info("File: " + e_file + " already exists.  Not moving.")

    else:
        logging.info("hasnicetitle is false.  Not moving files.")


def rename_files(oldpath, job):
    """
    Rename a directory and its contents based on job class details\n
    oldpath = Path to existing directory\n
    job = An instance of the Job class\n

    returns new path if successful
    """

    newpath = os.path.join(job.config.ARMPATH, job.title + " (" + str(job.year) + ")")
    logging.debug("oldpath: " + oldpath + " newpath: " + newpath)
    logging.info("Changing directory name from " + oldpath + " to " + newpath)

    ## Added from pull 366
    # Sometimes a job fails, after the rip, but before move of the tracks into the folder, at which point the below command
    # will move the newly ripped folder inside the old correctly named folder.
    # This can be a problem as the job when it tries to move the files, won't find them.
    # other than putting in an error message, I'm not sure how to perminently fix this problem.
    # Maybe I could add a configurable option for deletion of crashed job files?
    if os.path.isdir(newpath):
        logging.info("Error: The 'new' directory already exists, ARM will probably copy the newly ripped folder into the old-new folder.")

    try:
        shutil.move(oldpath, newpath)
        logging.debug("Directory name change successful")
    except shutil.Error:
        logging.info("Error change directory from " + oldpath + " to " + newpath + ".  Likely the path already exists.")
        raise OSError(2, 'No such file or directory', newpath)

    # try:
    #     shutil.rmtree(oldpath)
    #     logging.debug("oldpath deleted successfully.")
    # except shutil.Error:
    #     logging.info("Error change directory from " + oldpath + " to " + newpath + ".  Likely the path already exists.")
    #     raise OSError(2, 'No such file or directory', newpath)

    # tracks = Track.query.get(job.job_id)
    # tracks = job.tracks.all()
    # for track in tracks:
    #     if track.main_feature:
    #         newfilename = job.title + " (" + str(job.year) + ")" + "." + cfg["DEST_EXT"]
    #     else:
    #         newfilename = job.title + " (" + str(job.year) + ")" + track.track_number + "." + cfg["DEST_EXT"]

    #     track.new_filename = newfilename

    #     # newfullpath = os.path.join(newpath, job.new_title + " (" + str(job.new_year) + ")" + track.track_number + "." + cfg["DEST_EXT"])
    #     logging.info("Changing filename '" + os.path.join(newpath, track.filename) + "' to '" + os.path.join(newpath, newfilename) + "'")
    #     try:
    #         shutil.move(os.path.join(newpath, track.filename), os.path.join(newpath, newfilename))
    #         logging.debug("Filename change successful")
    #     except shutil.Error:
    #         logging.error("Unable to change '" + track.filename + "' to '" + newfilename + "'")
    #         raise OSError(3, 'Unable to change file', newfilename)

    #     track.filename = newfilename
        # db.session.commit()

    return newpath


def make_dir(path):
    """
Make a directory\n
    path = Path to directory\n

    returns success True if successful
        false if the directory already exists
    """
    if not os.path.exists(path):
        logging.debug("Creating directory: " + path)
        try:
            os.makedirs(path)
            return True
        except OSError:
            err = "Couldn't create a directory at path: " + path + " Probably a permissions error.  Exiting"
            logging.error(err)
            sys.exit(err)
            # return False
    else:
        return False


def get_cdrom_status(devpath):
    """get the status of the cdrom drive\n
    devpath = path to cdrom\n

    returns int
    CDS_NO_INFO		0\n
    CDS_NO_DISC		1\n
    CDS_TRAY_OPEN		2\n
    CDS_DRIVE_NOT_READY	3\n
    CDS_DISC_OK		4\n

    see linux/cdrom.h for specifics\n
    """

    try:
        fd = os.open(devpath, os.O_RDONLY | os.O_NONBLOCK)
    except Exception:
        logging.info("Failed to open device " + devpath + " to check status.")
        exit(2)
    result = fcntl.ioctl(fd, 0x5326, 0)

    return result


def find_file(filename, search_path):
    """
    Check to see if file exists by searching a directory recursively\n
    filename = filename to look for\n
    search_path = path to search recursively\n

    returns True or False
    """

    for dirpath, dirnames, filenames in os.walk(search_path):
        if filename in filenames:
            return True
    return False


def rip_music(job, logfile):
    """
    Rip music CD using abcde using abcde config\n
    job = job object\n
    logfile = location of logfile\n

    returns True/False for success/fail
    """

    if job.disctype == "music":
        logging.info("Disc identified as music")
        cmd = 'abcde -d "{0}" >> "{1}" 2>&1'.format(
            job.devpath,
            logfile
        )

        logging.debug("Sending command: " + cmd)

        try:
            subprocess.check_output(
                cmd,
                shell=True
            ).decode("utf-8")
            logging.info("abcde call successful")
            return True
        except subprocess.CalledProcessError as ab_error:
            err = "Call to abcde failed with code: " + str(ab_error.returncode) + "(" + str(ab_error.output) + ")"
            logging.error(err)
            # sys.exit(err)

    return False


def rip_data(job, datapath, logfile):
    """
    Rip data disc using dd on the command line\n
    job = job object\n
    datapath = path to copy data to\n
    logfile = location of logfile\n

    returns True/False for success/fail
    """

    if job.disctype == "data":
        logging.info("Disc identified as data")

        if (job.label) == "":
            job.label = "datadisc"

        filename = os.path.join(datapath, job.label + ".iso")

        logging.info("Ripping data disc to: " + filename)

        ## Added from pull 366
        cmd = 'dd if="{0}" of="{1}" {2} 2>> {3}'.format(
            job.devpath,
            filename,
            cfg["DATA_RIP_PARAMETERS"],
            logfile
        )

        logging.debug("Sending command: " + cmd)

        try:
            subprocess.check_output(
                cmd,
                shell=True
            ).decode("utf-8")
            logging.info("Data rip call successful")
            return True
        except subprocess.CalledProcessError as dd_error:
            err = "Data rip failed with code: " + str(dd_error.returncode) + "(" + str(dd_error.output) + ")"
            logging.error(err)
            # sys.exit(err)

    return False


def set_permissions(job, directory_to_traverse):
    try:
        corrected_chmod_value = int(str(job.config.CHMOD_VALUE), 8)
        logging.info("Setting permissions to: " + str(job.config.CHMOD_VALUE) + " on: " + directory_to_traverse)
        os.chmod(directory_to_traverse, corrected_chmod_value)

        for dirpath, l_directories, l_files in os.walk(directory_to_traverse):
            for cur_dir in l_directories:
                logging.debug("Setting path: " + cur_dir + " to permissions value: " + str(job.config.CHMOD_VALUE))
                os.chmod(os.path.join(dirpath, cur_dir), corrected_chmod_value)
            for cur_file in l_files:
                logging.debug("Setting file: " + cur_file + " to permissions value: " + str(job.config.CHMOD_VALUE))
                os.chmod(os.path.join(dirpath, cur_file), corrected_chmod_value)
        return True
    except Exception as e:
        err = "Permissions setting failed as: " + str(e)
        logging.error(err)
        return False


def check_db_version(install_path, db_file):
    """
    Check if db exists and is up to date.
    If it doesn't exist create it.  If it's out of date update it.
    """
    from alembic.script import ScriptDirectory
    from alembic.config import Config
    import sqlite3
    import flask_migrate

    # db_file = job.config.DBFILE
    mig_dir = os.path.join(install_path, "arm/migrations")

    config = Config()
    config.set_main_option("script_location", mig_dir)
    script = ScriptDirectory.from_config(config)

    # create db file if it doesn't exist
    if not os.path.isfile(db_file):
        logging.info("No database found.  Initializing arm.db...")
        make_dir(os.path.dirname(db_file))
        with app.app_context():
            flask_migrate.upgrade(mig_dir)

        if not os.path.isfile(db_file):
            logging.error("Can't create database file.  This could be a permissions issue.  Exiting...")
            sys.exit()

    # check to see if db is at current revision
    head_revision = script.get_current_head()
    logging.debug("Head is: " + head_revision)

    conn = sqlite3.connect(db_file)
    c = conn.cursor()

    c.execute("SELECT {cn} FROM {tn}".format(cn="version_num", tn="alembic_version"))
    db_version = c.fetchone()[0]
    logging.debug("Database version is: " + db_version)
    if head_revision == db_version:
        logging.info("Database is up to date")
    else:
        logging.info("Database out of date. Head is " + head_revision + " and database is " + db_version + ".  Upgrading database...")
        with app.app_context():
            ts = round(time.time() * 100)
            logging.info("Backuping up database '" + db_file + "' to '" + db_file + str(ts) + "'.")
            shutil.copy(db_file, db_file + "_" + str(ts))
            flask_migrate.upgrade(mig_dir)
        logging.info("Upgrade complete.  Validating version level...")

        c.execute("SELECT {cn} FROM {tn}".format(tn="alembic_version", cn="version_num"))
        db_version = c.fetchone()[0]
        logging.debug("Database version is: " + db_version)
        if head_revision == db_version:
            logging.info("Database is now up to date")
        else:
            logging.error("Database is still out of date. Head is " + head_revision + " and database is " + db_version + ".  Exiting arm.")
            sys.exit()


def put_track(job, t_no, seconds, aspect, fps, mainfeature, source, filename=""):
    """
    Put data into a track instance\n


    job = job ID\n
    t_no = track number\n
    seconds = lenght of track in seconds\n
    aspect = aspect ratio (ie '16:9')\n
    fps = frames per second (float)\n
    mainfeature = True/False\n
    source = Source of information\n
    filename = filename of track\n
    """

    logging.debug("Track #" + str(t_no) + " Length: " + str(seconds) + " fps: " + str(fps) + " aspect: " + str(aspect) + " Mainfeature: " +
                  str(mainfeature) + " Source: " + source)

    t = Track(
        job_id=job.job_id,
        track_number=t_no,
        length=seconds,
        aspect_ratio=aspect,
        # blocks=b,
        fps=fps,
        main_feature=mainfeature,
        source=source,
        basename=job.title,
        filename=filename
        )
    db.session.add(t)
    db.session.commit()
