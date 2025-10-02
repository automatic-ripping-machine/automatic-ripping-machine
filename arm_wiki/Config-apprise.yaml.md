# The apprise.yaml config file

## Overview

Apprise allows ARM to send notifications via multiple communication methods, as a single notificaiton or using multiple services at once.
The configuration file 'apprise.yaml' requires configuration to interact with the various notification services.
Its **strongly** advised to set at least one of these up when first setting up ARM. These notifications make solving problems much easier. 

## Setup

The default location for the apprise configuration when using docker is `/etc/arm/config/apprise.yaml`.
On installation ARM will copy the default (blank) configuration from the ARM setup
[apprise.yaml](https://github.com/automatic-ripping-machine/automatic-ripping-machine/blob/main/setup/apprise.yaml) into the docker container configuration.

1. From the ARM Settings / Ripper Settings page, set the apprise.yml location

    Default Location:
    **APPRISE:** /etc/arm/config/apprise.yaml

2. Save the configuration
3. From the ARM Settings / Apprise Config page, set the ID, Code, Webhook or other details for the required service.
4. Save the configration.
5. To test the configuration, from the ARM Settings / Apprise Config page select 'Send Test Notification'. 

    ARM will send a test notification, like the below, via the configured service(s).
    ```
    [ServerTest] - ARM Notification
    This is a notification by the ARM-Notification Test!
    ```

## Additional Configuration

ARM can provide additional information along with the notifications, through setting of the below fields.

**ARM Settings / Ripper Settings**

_NOTIFY_JOBID_
- True: Reports the ARM Job ID in the notification
- False: Reports only the status

_UI_BASE_URL_ and _WEBSERVER_PORT_
- Setting the UI Base URL and Webserver Port will send the server URL and Port rather than a docker localhost reference.
    Any links with a URL will send as `http://yourserver.local:8080` rather than `http://127.0.0.1:8080`
  - Testing with the values set will return a different Test Apprise message,
    with the local URL set to confirm values are correct.

    ```
    [ServerTest] - ARM notification
    This is a notification by the ARM-Notification Test! Server URL: http://yourserver.local:8080/
    ```

## Notification Services

[Apprise](https://github.com/caronc/apprise/wiki) does support more methods than are listed here. 
If you would like a services added to ARM that is not yet listed here, please open an issue or submit a pull request.

**Supported Services**. 

  - LaMetric
  - Mailgun
  - Boxcar
  - Discord
  - Fast
  - Flock
  - Gitter
  - Gotify
  - Growl
  - Join
  - Kodi
  - Kumulos
  - Matrix
  - Nextcloud
  - Notica
  - Notifico
  - Office365
  - Popcorn
  - Prowl
  - Pushjet
  - Push
  - Pushed
  - Rocketchat
  - Ryver 
  - Sendgrid
  - Simplepush
  - Slack
  - Spark
  - Spontit
  - Telegram
  - Twist
  - XBMC
  - XMPP
  - Webex teams
  - Zilup

## Service Specific Configurations

- **Gotify**
    - The Gotify settings expect a server address in one of the following formats:
    ```
    https://[GOTIFY-IP-ADDRESS]
    http://[GOTIFY-IP-ADDRESS]
    ```
    - Use **https** if your Gotify server is configured with SSL/TLS (**secure connection**).
    - Use **http** if your Gotify server is **not** configured with SSL/TLS (**insecure connection**).
  
