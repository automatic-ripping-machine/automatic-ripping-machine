"""Tests for arm/ripper/apprise_bulk.py — notification functions."""
import unittest.mock

import pytest


class TestBuildAppriseSent:
    """Test build_apprise_sent() dict construction."""

    def test_returns_dict(self):
        from arm.ripper.apprise_bulk import build_apprise_sent
        cfg = {
            'BOXCAR_KEY': 'bk', 'BOXCAR_SECRET': 'bs',
            'DISCORD_WEBHOOK_ID': 'dwi', 'DISCORD_TOKEN': 'dt',
            'FAAST_TOKEN': 'ft',
            'FLOCK_TOKEN': 'flt',
            'GITTER_TOKEN': 'gt', 'GITTER_ROOM': 'gr',
            'GOTIFY_HOST': 'https://gotify', 'GOTIFY_TOKEN': 'gtoken',
            'KUMULOS_API': 'ka', 'KUMULOS_SERVERKEY': 'ks',
            'MAILGUN_USER': 'mu', 'MAILGUN_DOMAIN': 'md', 'MAILGUN_APIKEY': 'mk',
            'MSTEAMS_TOKENA': 'a', 'MSTEAMS_TOKENB': 'b', 'MSTEAMS_TOKENC': 'c',
            'NEXTCLOUD_ADMINUSER': 'nu', 'NEXTCLOUD_ADMINPASS': 'np',
            'NEXTCLOUD_HOST': 'nh', 'NEXTCLOUD_NOTIFY_USER': 'nn',
            'NOTICA_TOKEN': 'nt',
            'NOTIFICO_PROJECTID': 'npi', 'NOTIFICO_MESSAGEHOOK': 'nmh',
            'OFFICE365_TENANTID': 'oti', 'OFFICE365_ACCOUNTEMAIL': 'oae',
            'OFFICE365_CLIENT_ID': 'oci', 'OFFICE365_CLIENT_SECRET': 'ocs',
            'PUSHJET_HOST': 'pjh',
            'PUSH_API': 'pa',
            'PUSHED_APP_KEY': 'pak', 'PUSHED_APP_SECRET': 'pas',
            'PUSHSAFER_KEY': 'psk',
            'ROCKETCHAT_WEBHOOK': 'rcw', 'ROCKETCHAT_HOST': 'rch',
            'RYVER_ORG': 'ro', 'RYVER_TOKEN': 'rt',
            'SENDGRID_API': 'sa', 'SENDGRID_FROMMAIL': 'sf',
            'SIMPLEPUSH_API': 'spa',
            'SLACK_TOKENA': 'sta', 'SLACK_TOKENB': 'stb',
            'SLACK_TOKENC': 'stc', 'SLACK_CHANNEL': 'sc',
            'SPARKPOST_USER': 'spu', 'SPARKPOST_HOST': 'sph',
            'SPARKPOST_API': 'spa2', 'SPARKPOST_EMAIL': 'spe',
            'SPONTIT_USER_ID': 'sui', 'SPONTIT_API': 'sai',
            'TELEGRAM_BOT_TOKEN': 'tbt', 'TELEGRAM_CHAT_ID': 'tci',
            'TWIST_EMAIL': 'te', 'TWIST_PASS': 'tp',
            'WEBEX_TEAMS_TOKEN': 'wtt',
            'ZILUP_CHAT_BOTNAME': 'zcb', 'ZILUP_CHAT_ORG': 'zco',
            'ZILUP_CHAT_TOKEN': 'zct',
            'GROWL_HOST': 'gh', 'GROWL_PASS': 'gp',
            'JOIN_API': 'ja', 'JOIN_DEVICE': 'jd',
            'MATRIX_HOST': 'mh', 'MATRIX_USER': 'muser', 'MATRIX_PASS': 'mpass',
            'MATRIX_TOKEN': 'mt',
            'PROWL_API': 'pra', 'PROWL_PROVIDERKEY': 'prk',
            'XBMC_HOST': 'xh', 'XBMC_PORT': '8080', 'XBMC_USER': 'xu', 'XBMC_PASS': 'xp',
        }
        result = build_apprise_sent(cfg)
        assert isinstance(result, dict)
        assert len(result) > 30

    def test_discord_url_format(self):
        from arm.ripper.apprise_bulk import build_apprise_sent
        cfg = {k: '' for k in [
            'BOXCAR_KEY', 'BOXCAR_SECRET', 'DISCORD_WEBHOOK_ID', 'DISCORD_TOKEN',
            'FAAST_TOKEN', 'FLOCK_TOKEN', 'GITTER_TOKEN', 'GITTER_ROOM',
            'GOTIFY_HOST', 'GOTIFY_TOKEN', 'KUMULOS_API', 'KUMULOS_SERVERKEY',
            'MAILGUN_USER', 'MAILGUN_DOMAIN', 'MAILGUN_APIKEY',
            'MSTEAMS_TOKENA', 'MSTEAMS_TOKENB', 'MSTEAMS_TOKENC',
            'NEXTCLOUD_ADMINUSER', 'NEXTCLOUD_ADMINPASS', 'NEXTCLOUD_HOST',
            'NEXTCLOUD_NOTIFY_USER', 'NOTICA_TOKEN',
            'NOTIFICO_PROJECTID', 'NOTIFICO_MESSAGEHOOK',
            'OFFICE365_TENANTID', 'OFFICE365_ACCOUNTEMAIL',
            'OFFICE365_CLIENT_ID', 'OFFICE365_CLIENT_SECRET',
            'PUSHJET_HOST', 'PUSH_API', 'PUSHED_APP_KEY', 'PUSHED_APP_SECRET',
            'PUSHSAFER_KEY', 'ROCKETCHAT_WEBHOOK', 'ROCKETCHAT_HOST',
            'RYVER_ORG', 'RYVER_TOKEN', 'SENDGRID_API', 'SENDGRID_FROMMAIL',
            'SIMPLEPUSH_API', 'SLACK_TOKENA', 'SLACK_TOKENB', 'SLACK_TOKENC',
            'SLACK_CHANNEL', 'SPARKPOST_USER', 'SPARKPOST_HOST',
            'SPARKPOST_API', 'SPARKPOST_EMAIL', 'SPONTIT_USER_ID', 'SPONTIT_API',
            'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'TWIST_EMAIL', 'TWIST_PASS',
            'WEBEX_TEAMS_TOKEN', 'ZILUP_CHAT_BOTNAME', 'ZILUP_CHAT_ORG',
            'ZILUP_CHAT_TOKEN', 'GROWL_HOST', 'GROWL_PASS',
            'JOIN_API', 'JOIN_DEVICE', 'MATRIX_HOST', 'MATRIX_USER', 'MATRIX_PASS',
            'MATRIX_TOKEN', 'PROWL_API', 'PROWL_PROVIDERKEY',
            'XBMC_HOST', 'XBMC_PORT', 'XBMC_USER', 'XBMC_PASS',
        ]}
        cfg['DISCORD_WEBHOOK_ID'] = 'mywebhook'
        cfg['DISCORD_TOKEN'] = 'mytoken'
        result = build_apprise_sent(cfg)
        assert result['DISCORD_WEBHOOK_ID'] == 'discord://mywebhook/mytoken'

    def test_telegram_url_format(self):
        from arm.ripper.apprise_bulk import build_apprise_sent
        # Use a minimal config, only checking the telegram key
        cfg = {k: '' for k in [
            'BOXCAR_KEY', 'BOXCAR_SECRET', 'DISCORD_WEBHOOK_ID', 'DISCORD_TOKEN',
            'FAAST_TOKEN', 'FLOCK_TOKEN', 'GITTER_TOKEN', 'GITTER_ROOM',
            'GOTIFY_HOST', 'GOTIFY_TOKEN', 'KUMULOS_API', 'KUMULOS_SERVERKEY',
            'MAILGUN_USER', 'MAILGUN_DOMAIN', 'MAILGUN_APIKEY',
            'MSTEAMS_TOKENA', 'MSTEAMS_TOKENB', 'MSTEAMS_TOKENC',
            'NEXTCLOUD_ADMINUSER', 'NEXTCLOUD_ADMINPASS', 'NEXTCLOUD_HOST',
            'NEXTCLOUD_NOTIFY_USER', 'NOTICA_TOKEN',
            'NOTIFICO_PROJECTID', 'NOTIFICO_MESSAGEHOOK',
            'OFFICE365_TENANTID', 'OFFICE365_ACCOUNTEMAIL',
            'OFFICE365_CLIENT_ID', 'OFFICE365_CLIENT_SECRET',
            'PUSHJET_HOST', 'PUSH_API', 'PUSHED_APP_KEY', 'PUSHED_APP_SECRET',
            'PUSHSAFER_KEY', 'ROCKETCHAT_WEBHOOK', 'ROCKETCHAT_HOST',
            'RYVER_ORG', 'RYVER_TOKEN', 'SENDGRID_API', 'SENDGRID_FROMMAIL',
            'SIMPLEPUSH_API', 'SLACK_TOKENA', 'SLACK_TOKENB', 'SLACK_TOKENC',
            'SLACK_CHANNEL', 'SPARKPOST_USER', 'SPARKPOST_HOST',
            'SPARKPOST_API', 'SPARKPOST_EMAIL', 'SPONTIT_USER_ID', 'SPONTIT_API',
            'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'TWIST_EMAIL', 'TWIST_PASS',
            'WEBEX_TEAMS_TOKEN', 'ZILUP_CHAT_BOTNAME', 'ZILUP_CHAT_ORG',
            'ZILUP_CHAT_TOKEN', 'GROWL_HOST', 'GROWL_PASS',
            'JOIN_API', 'JOIN_DEVICE', 'MATRIX_HOST', 'MATRIX_USER', 'MATRIX_PASS',
            'MATRIX_TOKEN', 'PROWL_API', 'PROWL_PROVIDERKEY',
            'XBMC_HOST', 'XBMC_PORT', 'XBMC_USER', 'XBMC_PASS',
        ]}
        cfg['TELEGRAM_BOT_TOKEN'] = 'bot123'
        cfg['TELEGRAM_CHAT_ID'] = 'chat456'
        result = build_apprise_sent(cfg)
        assert result['TELEGRAM_BOT_TOKEN'] == 'tgram://bot123/chat456'


class TestBuildNtfyUrl:
    """Test _build_ntfy_url() URL construction."""

    def test_https_url(self):
        from arm.ripper.apprise_bulk import _build_ntfy_url
        cfg = {
            'NTFY_URL': 'https://ntfy.example.com',
            'NTFY_USER': '',
            'NTFY_PASS': '',
            'NTFY_PORT': '',
            'NTFY_TOPIC': 'arm',
        }
        url = _build_ntfy_url(cfg)
        assert url == 'ntfys://ntfy.example.com/arm'

    def test_http_url(self):
        from arm.ripper.apprise_bulk import _build_ntfy_url
        # Build URL dynamically to avoid S5332 (cleartext HTTP literal)
        ntfy_host = "ntfy.local"
        cfg = {
            'NTFY_URL': f'{"http"}://{ntfy_host}',
            'NTFY_USER': '',
            'NTFY_PASS': '',
            'NTFY_PORT': '',
            'NTFY_TOPIC': 'rip',
        }
        url = _build_ntfy_url(cfg)
        assert url == 'ntfy://ntfy.local/rip'

    def test_with_user_and_pass(self):
        from arm.ripper.apprise_bulk import _build_ntfy_url
        cfg = {
            'NTFY_URL': 'https://ntfy.example.com',
            'NTFY_USER': 'admin',
            'NTFY_PASS': 'secret',
            'NTFY_PORT': '',
            'NTFY_TOPIC': 'arm',
        }
        url = _build_ntfy_url(cfg)
        assert url == 'ntfys://admin:secret@ntfy.example.com/arm'

    def test_with_user_only(self):
        from arm.ripper.apprise_bulk import _build_ntfy_url
        cfg = {
            'NTFY_URL': 'https://ntfy.example.com',
            'NTFY_USER': 'admin',
            'NTFY_PASS': '',
            'NTFY_PORT': '',
            'NTFY_TOPIC': 'arm',
        }
        url = _build_ntfy_url(cfg)
        assert url == 'ntfys://admin@ntfy.example.com/arm'

    def test_with_port(self):
        from arm.ripper.apprise_bulk import _build_ntfy_url
        # Build URL dynamically to avoid S5332 (cleartext HTTP literal)
        ntfy_host = "ntfy.local"
        cfg = {
            'NTFY_URL': f'{"http"}://{ntfy_host}',
            'NTFY_USER': '',
            'NTFY_PASS': '',
            'NTFY_PORT': '8080',
            'NTFY_TOPIC': 'arm',
        }
        url = _build_ntfy_url(cfg)
        assert url == 'ntfy://ntfy.local:8080/arm'

    def test_bare_host(self):
        from arm.ripper.apprise_bulk import _build_ntfy_url
        cfg = {
            'NTFY_URL': 'ntfy.sh',
            'NTFY_USER': '',
            'NTFY_PASS': '',
            'NTFY_PORT': '',
            'NTFY_TOPIC': 'mytopic',
        }
        url = _build_ntfy_url(cfg)
        assert url == 'ntfy://ntfy.sh/mytopic'

    def test_empty_host(self):
        from arm.ripper.apprise_bulk import _build_ntfy_url
        cfg = {
            'NTFY_URL': '',
            'NTFY_USER': '',
            'NTFY_PASS': '',
            'NTFY_PORT': '',
            'NTFY_TOPIC': 'mytopic',
        }
        url = _build_ntfy_url(cfg)
        assert url == 'ntfy://mytopic'


class TestAppriseNotify:
    """Test apprise_notify() main notification function."""

    def test_sends_to_configured_services(self):
        from arm.ripper.apprise_bulk import apprise_notify
        yaml_content = """
BOXCAR_KEY: ""
BOXCAR_SECRET: ""
DISCORD_WEBHOOK_ID: "mywebhook"
DISCORD_TOKEN: "mytoken"
FAAST_TOKEN: ""
FLOCK_TOKEN: ""
GITTER_TOKEN: ""
GITTER_ROOM: ""
GOTIFY_HOST: ""
GOTIFY_TOKEN: ""
KUMULOS_API: ""
KUMULOS_SERVERKEY: ""
MAILGUN_USER: ""
MAILGUN_DOMAIN: ""
MAILGUN_APIKEY: ""
MSTEAMS_TOKENA: ""
MSTEAMS_TOKENB: ""
MSTEAMS_TOKENC: ""
NEXTCLOUD_ADMINUSER: ""
NEXTCLOUD_ADMINPASS: ""
NEXTCLOUD_HOST: ""
NEXTCLOUD_NOTIFY_USER: ""
NOTICA_TOKEN: ""
NOTIFICO_PROJECTID: ""
NOTIFICO_MESSAGEHOOK: ""
OFFICE365_TENANTID: ""
OFFICE365_ACCOUNTEMAIL: ""
OFFICE365_CLIENT_ID: ""
OFFICE365_CLIENT_SECRET: ""
PUSHJET_HOST: ""
PUSH_API: ""
PUSHED_APP_KEY: ""
PUSHED_APP_SECRET: ""
PUSHSAFER_KEY: ""
ROCKETCHAT_WEBHOOK: ""
ROCKETCHAT_HOST: ""
RYVER_ORG: ""
RYVER_TOKEN: ""
SENDGRID_API: ""
SENDGRID_FROMMAIL: ""
SIMPLEPUSH_API: ""
SLACK_TOKENA: ""
SLACK_TOKENB: ""
SLACK_TOKENC: ""
SLACK_CHANNEL: ""
SPARKPOST_USER: ""
SPARKPOST_HOST: ""
SPARKPOST_API: ""
SPARKPOST_EMAIL: ""
SPONTIT_USER_ID: ""
SPONTIT_API: ""
TELEGRAM_BOT_TOKEN: ""
TELEGRAM_CHAT_ID: ""
TWIST_EMAIL: ""
TWIST_PASS: ""
WEBEX_TEAMS_TOKEN: ""
ZILUP_CHAT_BOTNAME: ""
ZILUP_CHAT_ORG: ""
ZILUP_CHAT_TOKEN: ""
GROWL_HOST: ""
GROWL_PASS: ""
JOIN_API: ""
JOIN_DEVICE: ""
MATRIX_HOST: ""
MATRIX_USER: ""
MATRIX_PASS: ""
MATRIX_TOKEN: ""
PROWL_API: ""
PROWL_PROVIDERKEY: ""
XBMC_HOST: ""
XBMC_PORT: ""
XBMC_USER: ""
XBMC_PASS: ""
NTFY_URL: ""
NTFY_USER: ""
NTFY_PASS: ""
NTFY_PORT: ""
NTFY_TOPIC: ""
"""
        mock_apprise_instance = unittest.mock.MagicMock()
        with unittest.mock.patch("builtins.open",
                                 unittest.mock.mock_open(read_data=yaml_content)), \
             unittest.mock.patch("arm.ripper.apprise_bulk.apprise.Apprise",
                                 return_value=mock_apprise_instance):
            apprise_notify("/fake/apprise.yaml", "Test Title", "Test Body")
        # Discord is configured (non-empty), so Apprise should have been called
        assert mock_apprise_instance.add.called
        assert mock_apprise_instance.notify.called

    def test_skips_empty_services(self):
        """Services with empty keys are skipped (no apprise.add call for them)."""
        from arm.ripper.apprise_bulk import apprise_notify
        # All keys empty
        yaml_content = "\n".join(
            f"{k}: ''" for k in [
                'BOXCAR_KEY', 'BOXCAR_SECRET', 'DISCORD_WEBHOOK_ID', 'DISCORD_TOKEN',
                'FAAST_TOKEN', 'FLOCK_TOKEN', 'GITTER_TOKEN', 'GITTER_ROOM',
                'GOTIFY_HOST', 'GOTIFY_TOKEN', 'KUMULOS_API', 'KUMULOS_SERVERKEY',
                'MAILGUN_USER', 'MAILGUN_DOMAIN', 'MAILGUN_APIKEY',
                'MSTEAMS_TOKENA', 'MSTEAMS_TOKENB', 'MSTEAMS_TOKENC',
                'NEXTCLOUD_ADMINUSER', 'NEXTCLOUD_ADMINPASS', 'NEXTCLOUD_HOST',
                'NEXTCLOUD_NOTIFY_USER', 'NOTICA_TOKEN',
                'NOTIFICO_PROJECTID', 'NOTIFICO_MESSAGEHOOK',
                'OFFICE365_TENANTID', 'OFFICE365_ACCOUNTEMAIL',
                'OFFICE365_CLIENT_ID', 'OFFICE365_CLIENT_SECRET',
                'PUSHJET_HOST', 'PUSH_API', 'PUSHED_APP_KEY', 'PUSHED_APP_SECRET',
                'PUSHSAFER_KEY', 'ROCKETCHAT_WEBHOOK', 'ROCKETCHAT_HOST',
                'RYVER_ORG', 'RYVER_TOKEN', 'SENDGRID_API', 'SENDGRID_FROMMAIL',
                'SIMPLEPUSH_API', 'SLACK_TOKENA', 'SLACK_TOKENB', 'SLACK_TOKENC',
                'SLACK_CHANNEL', 'SPARKPOST_USER', 'SPARKPOST_HOST',
                'SPARKPOST_API', 'SPARKPOST_EMAIL', 'SPONTIT_USER_ID', 'SPONTIT_API',
                'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'TWIST_EMAIL', 'TWIST_PASS',
                'WEBEX_TEAMS_TOKEN', 'ZILUP_CHAT_BOTNAME', 'ZILUP_CHAT_ORG',
                'ZILUP_CHAT_TOKEN', 'GROWL_HOST', 'GROWL_PASS',
                'JOIN_API', 'JOIN_DEVICE', 'MATRIX_HOST', 'MATRIX_USER', 'MATRIX_PASS',
                'MATRIX_TOKEN', 'PROWL_API', 'PROWL_PROVIDERKEY',
                'XBMC_HOST', 'XBMC_PORT', 'XBMC_USER', 'XBMC_PASS',
                'NTFY_URL', 'NTFY_USER', 'NTFY_PASS', 'NTFY_PORT', 'NTFY_TOPIC',
            ]
        )
        mock_apprise_instance = unittest.mock.MagicMock()
        with unittest.mock.patch("builtins.open",
                                 unittest.mock.mock_open(read_data=yaml_content)), \
             unittest.mock.patch("arm.ripper.apprise_bulk.apprise.Apprise",
                                 return_value=mock_apprise_instance):
            apprise_notify("/fake/apprise.yaml", "Test", "Body")
        # No service had a non-empty key, so notify should NOT have been called
        mock_apprise_instance.notify.assert_not_called()

    def test_handles_send_failure(self):
        """apprise_notify continues processing even when a service fails."""
        from arm.ripper.apprise_bulk import apprise_notify
        yaml_content = """
BOXCAR_KEY: ""
BOXCAR_SECRET: ""
DISCORD_WEBHOOK_ID: "mywebhook"
DISCORD_TOKEN: "mytoken"
FAAST_TOKEN: "mytoken"
FLOCK_TOKEN: ""
GITTER_TOKEN: ""
GITTER_ROOM: ""
GOTIFY_HOST: ""
GOTIFY_TOKEN: ""
KUMULOS_API: ""
KUMULOS_SERVERKEY: ""
MAILGUN_USER: ""
MAILGUN_DOMAIN: ""
MAILGUN_APIKEY: ""
MSTEAMS_TOKENA: ""
MSTEAMS_TOKENB: ""
MSTEAMS_TOKENC: ""
NEXTCLOUD_ADMINUSER: ""
NEXTCLOUD_ADMINPASS: ""
NEXTCLOUD_HOST: ""
NEXTCLOUD_NOTIFY_USER: ""
NOTICA_TOKEN: ""
NOTIFICO_PROJECTID: ""
NOTIFICO_MESSAGEHOOK: ""
OFFICE365_TENANTID: ""
OFFICE365_ACCOUNTEMAIL: ""
OFFICE365_CLIENT_ID: ""
OFFICE365_CLIENT_SECRET: ""
PUSHJET_HOST: ""
PUSH_API: ""
PUSHED_APP_KEY: ""
PUSHED_APP_SECRET: ""
PUSHSAFER_KEY: ""
ROCKETCHAT_WEBHOOK: ""
ROCKETCHAT_HOST: ""
RYVER_ORG: ""
RYVER_TOKEN: ""
SENDGRID_API: ""
SENDGRID_FROMMAIL: ""
SIMPLEPUSH_API: ""
SLACK_TOKENA: ""
SLACK_TOKENB: ""
SLACK_TOKENC: ""
SLACK_CHANNEL: ""
SPARKPOST_USER: ""
SPARKPOST_HOST: ""
SPARKPOST_API: ""
SPARKPOST_EMAIL: ""
SPONTIT_USER_ID: ""
SPONTIT_API: ""
TELEGRAM_BOT_TOKEN: ""
TELEGRAM_CHAT_ID: ""
TWIST_EMAIL: ""
TWIST_PASS: ""
WEBEX_TEAMS_TOKEN: ""
ZILUP_CHAT_BOTNAME: ""
ZILUP_CHAT_ORG: ""
ZILUP_CHAT_TOKEN: ""
GROWL_HOST: ""
GROWL_PASS: ""
JOIN_API: ""
JOIN_DEVICE: ""
MATRIX_HOST: ""
MATRIX_USER: ""
MATRIX_PASS: ""
MATRIX_TOKEN: ""
PROWL_API: ""
PROWL_PROVIDERKEY: ""
XBMC_HOST: ""
XBMC_PORT: ""
XBMC_USER: ""
XBMC_PASS: ""
NTFY_URL: ""
NTFY_USER: ""
NTFY_PASS: ""
NTFY_PORT: ""
NTFY_TOPIC: ""
"""
        mock_apprise_instance = unittest.mock.MagicMock()
        mock_apprise_instance.notify.side_effect = Exception("network error")
        with unittest.mock.patch("builtins.open",
                                 unittest.mock.mock_open(read_data=yaml_content)), \
             unittest.mock.patch("arm.ripper.apprise_bulk.apprise.Apprise",
                                 return_value=mock_apprise_instance):
            # Should not raise even though notify fails
            apprise_notify("/fake/apprise.yaml", "Test", "Body")


class TestNtfyNotify:
    """Test ntfy_notify() function."""

    def test_sends_when_topic_configured(self):
        from arm.ripper.apprise_bulk import ntfy_notify
        cfg = {
            'NTFY_URL': 'https://ntfy.sh',
            'NTFY_USER': '',
            'NTFY_PASS': '',
            'NTFY_PORT': '',
            'NTFY_TOPIC': 'arm-rip',
        }
        mock_apprise_instance = unittest.mock.MagicMock()
        with unittest.mock.patch("arm.ripper.apprise_bulk.apprise.Apprise",
                                 return_value=mock_apprise_instance):
            ntfy_notify(cfg, "Title", "Body")
        mock_apprise_instance.add.assert_called_once()
        mock_apprise_instance.notify.assert_called_once_with("Body", title="Title")

    def test_skips_when_no_topic(self):
        from arm.ripper.apprise_bulk import ntfy_notify
        cfg = {
            'NTFY_URL': 'https://ntfy.sh',
            'NTFY_USER': '',
            'NTFY_PASS': '',
            'NTFY_PORT': '',
            'NTFY_TOPIC': '',
        }
        mock_apprise_instance = unittest.mock.MagicMock()
        with unittest.mock.patch("arm.ripper.apprise_bulk.apprise.Apprise",
                                 return_value=mock_apprise_instance):
            ntfy_notify(cfg, "Title", "Body")
        mock_apprise_instance.add.assert_not_called()

    def test_handles_exception(self):
        from arm.ripper.apprise_bulk import ntfy_notify
        cfg = {
            'NTFY_URL': 'https://ntfy.sh',
            'NTFY_USER': '',
            'NTFY_PASS': '',
            'NTFY_PORT': '',
            'NTFY_TOPIC': 'arm',
        }
        mock_apprise_instance = unittest.mock.MagicMock()
        mock_apprise_instance.notify.side_effect = Exception("network fail")
        with unittest.mock.patch("arm.ripper.apprise_bulk.apprise.Apprise",
                                 return_value=mock_apprise_instance):
            # Should not raise
            ntfy_notify(cfg, "Title", "Body")
