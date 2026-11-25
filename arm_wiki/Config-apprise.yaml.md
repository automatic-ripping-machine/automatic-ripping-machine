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
  - Email
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

### **Email**

ARM builds a standard `mailto://` apprise URL from the `EMAIL_*` entries, so any
address apprise has a template for works, including Fastmail. The settings are:

| Setting | Meaning |
|---|---|
| `EMAIL_FROM` | The sender address. Leave it blank to turn email notifications off. |
| `EMAIL_USER` | Login for the SMTP server. Leave it blank to log in as `EMAIL_FROM`. |
| `EMAIL_PASS` | Password for that login. Leave it blank for a relay that needs no login. |
| `EMAIL_TO` | Comma separated list of recipients. |
| `EMAIL_SMTP_HOST` | SMTP server. Leave it blank to use the sender address' own provider. |
| `EMAIL_SMTP_PORT` | SMTP port. Leave it blank to use the port that matches `EMAIL_SECURE_MODE`. |
| `EMAIL_SECURE_MODE` | `ssl`, `starttls`, `insecure`, or blank to let apprise decide. |

For Fastmail, leave the host, port and mode blank and give a
[app password](https://www.fastmail.help/hc/en-us/articles/360058752854-App-passwords)
in `EMAIL_PASS`: apprise already knows that `fastmail.com` means
`smtp.fastmail.com` on port 465 with SSL.

```yaml
EMAIL_FROM: "ripper@fastmail.com"
EMAIL_USER: ""
EMAIL_PASS: "app-password-from-fastmail"
EMAIL_TO: "phone@example.com"
EMAIL_SMTP_HOST: ""
EMAIL_SMTP_PORT: ""
EMAIL_SECURE_MODE: ""
```

### **Gotify**

The Gotify settings expect a server address in one of the following formats:

```
gotifys://[GOTIFY-ADDRESS]
gotify://[GOTIFY-ADDRESS]
```

- Use **gotifys** if your Gotify server is configured with SSL/TLS (**secure connection**).
- Use **gotify** if your Gotify server is **not** configured with SSL/TLS (**insecure connection**).
