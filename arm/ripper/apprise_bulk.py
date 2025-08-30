"""File to hold all functions pertaining to apprise"""
import logging
import yaml
import apprise


# TODO: Refactor this to leverage apprise_config stored in config.py
def build_apprise_sent(cfg):
    """
    Build dict for processing
    :param cfg: apprise.yaml loaded as dict
    :return: dict with key -> link
    """
    apprise_dict = {
        'BOXCAR_KEY': 'boxcar://' + str(cfg['BOXCAR_KEY']) + "/" + str(cfg['BOXCAR_SECRET']),
        'DISCORD_WEBHOOK_ID': 'discord://' + str(cfg['DISCORD_WEBHOOK_ID']) + "/" + str(cfg['DISCORD_TOKEN']),
        'FAAST_TOKEN': 'faast://' + str(cfg['FAAST_TOKEN']),
        'FLOCK_TOKEN': 'flock://' + str(cfg['FLOCK_TOKEN']),
        'GITTER_TOKEN': 'gitter://' + str(cfg['GITTER_TOKEN']) + "/" + str(cfg['GITTER_ROOM']),
        'GOTIFY_TOKEN': str(cfg['GOTIFY_HOST']) + "/" + str(cfg['GOTIFY_TOKEN']),
        'KUMULOS_API': 'kumulos://' + str(cfg['KUMULOS_API']) + "/" + str(cfg['KUMULOS_SERVERKEY']),
        'MAILGUN_DOMAIN': 'mailgun://' + str(cfg['MAILGUN_USER']) + "@" + str(cfg['MAILGUN_DOMAIN']) + "/"
                          + str(cfg['MAILGUN_APIKEY']),
        'MSTEAMS_TOKENA': 'msteams://' + str(cfg['MSTEAMS_TOKENA']) + "/" + str(cfg['MSTEAMS_TOKENB']) + "/" + str(
            cfg['MSTEAMS_TOKENC']) + "/",
        'NEXTCLOUD_HOST': 'nclouds://' + str(cfg['NEXTCLOUD_ADMINUSER']) + ":" + str(cfg['NEXTCLOUD_ADMINPASS'])
                          + "@" + str(cfg['NEXTCLOUD_HOST']) + "/" + str(cfg['NEXTCLOUD_NOTIFY_USER']),
        'NOTICA_TOKEN': 'notica://' + str(cfg['NOTICA_TOKEN']),
        'NOTIFICO_PROJECTID': 'notifico://' + str(cfg['NOTIFICO_PROJECTID'])
                              + "/" + str(cfg['NOTIFICO_MESSAGEHOOK']),
        'OFFICE365_TENANTID': 'o365://' + str(cfg['OFFICE365_TENANTID'])
                              + ":" + str(cfg['OFFICE365_ACCOUNTEMAIL']) + "/"
                              + str(cfg['OFFICE365_CLIENT_ID'])
                              + "/" + str(cfg['OFFICE365_CLIENT_SECRET']),
        'PUSHJET_HOST': 'pjet://' + str(cfg['PUSHJET_HOST']),
        'PUSH_API': 'push://' + str(cfg['PUSH_API']),
        'PUSHED_APP_KEY': 'pushed://' + str(cfg['PUSHED_APP_KEY']) + "/" + str(cfg['PUSHED_APP_SECRET']),
        'PUSHSAFER_KEY': 'psafers://' + str(cfg['PUSHSAFER_KEY']),
        'ROCKETCHAT_HOST': 'rocket://' + str(cfg['ROCKETCHAT_WEBHOOK']) + "@" + str(cfg['ROCKETCHAT_HOST']),
        'RYVER_ORG': 'ryver://' + str(cfg['RYVER_ORG']) + "/" + str(cfg['RYVER_TOKEN']) + "/",
        'SENDGRID_API': 'sendgrid://' + str(cfg['SENDGRID_API']) + ":" + str(cfg['SENDGRID_FROMMAIL']),
        'SIMPLEPUSH_API': 'spush://' + str(cfg['SIMPLEPUSH_API']),
        'SLACK_TOKENA': 'slack://' + str(cfg['SLACK_TOKENA']) + "/" + str(cfg['SLACK_TOKENB']) + "/" + str(
            cfg['SLACK_TOKENC']) + "/" + str(cfg['SLACK_CHANNEL']),
        'SPARKPOST_API': 'sparkpost://' + str(cfg['SPARKPOST_USER']) + "@" + str(cfg['SPARKPOST_HOST']) + "/" + str(
            cfg['SPARKPOST_API']) + "/" + str(cfg['SPARKPOST_EMAIL']),
        'SPONTIT_API': 'spontit://' + str(cfg['SPONTIT_USER_ID']) + "@" + str(cfg['SPONTIT_API']),
        'TELEGRAM_BOT_TOKEN': 'tgram://' + str(cfg['TELEGRAM_BOT_TOKEN']) + "/" + str(cfg['TELEGRAM_CHAT_ID']),
        'TWIST_EMAIL': 'twist://' + str(cfg['TWIST_EMAIL']) + "/" + str(cfg['TWIST_PASS']),
        'WEBEX_TEAMS_TOKEN': 'wxteams://' + str(cfg['WEBEX_TEAMS_TOKEN']),
        'ZILUP_CHAT_TOKEN': 'zulip://' + str(cfg['ZILUP_CHAT_BOTNAME']) + "@" + str(cfg['ZILUP_CHAT_ORG']) + "/" + str(
            cfg['ZILUP_CHAT_TOKEN']),
        'GROWL_HOST': 'growl://' + str(cfg['GROWL_HOST']),
        'GROWL_PASS': 'growl://' + str(cfg['GROWL_PASS']) + "@" + str(cfg['GROWL_HOST']),
        'JOIN_API': 'join://' + str(cfg['JOIN_API']),
        'JOIN_DEVICE': 'join://' + str(cfg['JOIN_API']) + "/" + str(cfg['JOIN_DEVICE']),
        'MATRIX_HOST': 'matrixs://' + str(cfg['MATRIX_USER']) + ":" + str(cfg['MATRIX_PASS']) + "@" + str(
            cfg['MATRIX_HOST']),  # MATRIX_TOKEN
        'MATRIX_TOKEN': 'matrix://' + str(cfg['MATRIX_TOKEN']),  # MATRIX_TOKEN
        'PROWL_API': 'prowl://' + str(cfg['PROWL_API']),
        'PROWL_PROVIDERKEY': 'prowl://' + str(cfg['PROWL_API']) + "/" + str(cfg['PROWL_PROVIDERKEY']),
        'XBMC_HOST': 'xbmc://' + str(cfg['XBMC_HOST']) + ":" + str(cfg['XBMC_PORT']),
        'XBMC_USER': 'xbmc://' + str(cfg['XBMC_USER']) + ":" + str(cfg['XBMC_PASS']) + "@" + str(
            cfg['XBMC_HOST']) + ":" + str(cfg['XBMC_PORT']),
        #######################################################
        # Very special cases, may need to be triggered manually
        #######################################################
        'KODI_HOST': 'kodi://{0}/{1}',
        'LAMETRIC_MODE': 'lametric://{0}/{1}',
        'POPCORN_API': 'popcorn://{0}/{1}',

    }
    return apprise_dict


def apprise_notify(apprise_cfg, title, body):
    """
    APPRISE NOTIFICATIONS\n
    :param apprise_cfg: The full path to the apprise.yaml file
    :param title: the message title
    :param body: the main body of the message
    :return: None
    """
    with open(apprise_cfg, "r") as yaml_file:
        cfg = yaml.safe_load(yaml_file)

    sent_cfg = build_apprise_sent(cfg)
    for host, string in sent_cfg.items():
        try:
            #  logging.debug(f"trying to send apprise to {host}")
            if cfg[host] != "":
                # Create an Apprise instance
                apobj = apprise.Apprise()
                apobj.add(string)
                apobj.notify(body, title=title)
                logging.debug(f"Sent apprise to {host} was successful")
        except Exception as error:  # noqa: E722
            logging.error(f"Failed sending {host} apprise notification.  continuing  processing...{error}")

    ntfy_notify(cfg, title, body)


def ntfy_notify(cfg, title, body):
    # ntfy can require additional processing to make https work.
    # In addition, there are multiple available valid schemes.
    if cfg['NTFY_TOPIC'] != "":
        try:
            apobj = apprise.Apprise()
            ntfy_serverstring = 'ntfy://'

            host = cfg['NTFY_URL']

            if host.startswith("https://"):
                ntfy_serverstring = 'ntfys://'
                host = host.replace("https://", "")

            if host.startswith("http://"):
                host = host.replace("http://", "")

            if cfg['NTFY_USER'] != "" and cfg['NTFY_PASS'] != "" and host != "":
                ntfy_serverstring += cfg['NTFY_USER'] + ':' + cfg['NTFY_PASS'] + '@' + host

            elif cfg['NTFY_USER'] != "" and host != "":
                ntfy_serverstring += cfg['NTFY_USER'] + '@' + host

            elif host != "":
                ntfy_serverstring += host

            if host != "" and cfg['NTFY_PORT'] != "":
                ntfy_serverstring += ':' + cfg['NTFY_PORT'] + '/'
            else:
                if ntfy_serverstring != 'ntfy://':
                    ntfy_serverstring += '/'

            ntfy_serverstring += cfg['NTFY_TOPIC']

            print(ntfy_serverstring)
            apobj.add(ntfy_serverstring)
            apobj.notify(
                body,
                title=title,
            )
            logging.debug("Sent apprise to ntfy was successful")
        except Exception as error:  # noqa: E722
            logging.error(f"Failed sending ntfy apprise notification. Continuing  processing...{error}")
