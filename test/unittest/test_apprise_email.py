"""Email notifications built from the apprise.yaml EMAIL_* keys (#1908)."""

import socketserver
import threading

import pytest

import apprise

from arm.ripper import apprise_bulk

FASTMAIL = {
    "EMAIL_FROM": "ripper@fastmail.com",
    "EMAIL_USER": "",
    "EMAIL_PASS": "app password",
    "EMAIL_TO": "one@example.com, two@example.com",
    "EMAIL_SMTP_HOST": "",
    "EMAIL_SMTP_PORT": "",
    "EMAIL_SECURE_MODE": "",
}


def record_urls(cfg, title="ARM notification", body="Job 1 finished"):
    """The mailto:// URLs email_notify hands to apprise, without contacting a server."""
    added = []

    class RecordingApprise(apprise.Apprise):
        def add(self, servers, asset=None, tag=None):
            added.append(servers)
            return True

        def notify(self, body, title="", **kwargs):
            return True

    original = apprise_bulk.apprise.Apprise
    apprise_bulk.apprise.Apprise = RecordingApprise
    try:
        apprise_bulk.email_notify(cfg, title, body)
    finally:
        apprise_bulk.apprise.Apprise = original
    return added


def parsed(cfg):
    """Let apprise parse the URL we build, so assertions use the values it will really use."""
    added = record_urls(cfg)
    assert len(added) == 1
    plugin = apprise.Apprise.instantiate(added[0])
    assert plugin is not None, "apprise rejected the generated URL"
    return plugin


def test_fastmail_address_picks_the_fastmail_server():
    plugin = parsed(FASTMAIL)

    assert plugin.smtp_host == "smtp.fastmail.com"
    assert plugin.port == 465
    assert plugin.secure_mode == "ssl"
    assert plugin.from_addr == (False, "ripper@fastmail.com")
    assert plugin.targets == [(False, "one@example.com"), (False, "two@example.com")]


def test_fastmail_app_password_survives_the_round_trip():
    plugin = parsed(FASTMAIL)

    assert plugin.user == "ripper@fastmail.com"
    assert plugin.password == "app password"


def test_separate_login_user_is_used_for_the_smtp_login():
    cfg = dict(FASTMAIL, EMAIL_USER="login@example.com", EMAIL_PASS="s3cret/pw")
    plugin = parsed(cfg)

    assert plugin.user == "login@example.com"
    assert plugin.password == "s3cret/pw"
    assert plugin.from_addr == (False, "ripper@fastmail.com")


def test_explicit_server_and_port_override_the_defaults():
    cfg = dict(FASTMAIL, EMAIL_SMTP_HOST="mail.example.com", EMAIL_SMTP_PORT="2587")
    plugin = parsed(cfg)

    assert plugin.smtp_host == "mail.example.com"
    assert plugin.port == 2587


@pytest.mark.parametrize("mode,port", [("ssl", 465), ("starttls", 587), ("insecure", 25)])
def test_secure_mode_defaults_to_its_usual_port(mode, port):
    cfg = dict(FASTMAIL, EMAIL_SMTP_HOST="mail.example.com", EMAIL_SECURE_MODE=mode)
    plugin = parsed(cfg)

    assert plugin.secure_mode == mode
    assert plugin.port == port


def test_server_that_needs_no_login_sends_without_credentials():
    cfg = dict(FASTMAIL, EMAIL_USER="", EMAIL_PASS="", EMAIL_SMTP_HOST="localhost", EMAIL_SECURE_MODE="insecure")
    plugin = parsed(cfg)

    assert plugin.smtp_host == "localhost"
    assert not plugin.user
    assert not plugin.password
    assert plugin.targets == [(False, "one@example.com"), (False, "two@example.com")]


def test_blank_from_leaves_email_disabled():
    """Every other apprise.yaml entry is opt-in on a blank value, so a blank EMAIL_FROM must not send."""
    assert record_urls(dict(FASTMAIL, EMAIL_FROM="")) == []


def test_apprise_yaml_without_the_email_keys_still_works():
    """apprise.yaml files written before this change have none of the EMAIL_* keys."""
    assert record_urls({}) == []


def test_unknown_secure_mode_is_reported_instead_of_guessed():
    cfg = dict(FASTMAIL, EMAIL_SMTP_HOST="mail.example.com", EMAIL_SECURE_MODE="implicit")

    assert record_urls(cfg) == []


def test_blank_recipients_are_reported_instead_of_sending_to_the_sender():
    cfg = dict(FASTMAIL, EMAIL_TO=" , ")

    assert record_urls(cfg) == []


class _SMTPServer(socketserver.ThreadingTCPServer):
    """A minimal SMTP server, enough for apprise to deliver one message over plain SMTP.

    smtpd was removed in Python 3.12, so this only implements the verbs that a send uses.
    """

    allow_reuse_address = True
    daemon_threads = True

    def __init__(self):
        super().__init__(("localhost", 0), _SMTPHandler)
        self.sender = None
        self.recipients = []
        self.received = []


class _SMTPHandler(socketserver.StreamRequestHandler):
    def handle(self):
        self._reply("220 localhost ESMTP")
        while True:
            line = self.rfile.readline().decode("utf-8", "replace").strip()
            if not line:
                return
            verb = line.split(" ", 1)[0].upper()
            if verb in ("EHLO", "HELO"):
                # No extension lines: apprise then stays on plain SMTP with no login
                self._reply("250 localhost")
            elif verb == "MAIL":
                self.server.sender = line.split("FROM:", 1)[-1].strip(" <>")
                self._reply("250 OK")
            elif verb == "RCPT":
                self.server.recipients.append(line.split(":", 1)[1].strip(" <>"))
                self._reply("250 OK")
            elif verb == "DATA":
                self._reply("354 End data with <CR><LF>.<CR><LF>")
                self.server.received.append(
                    (self.server.sender, list(self.server.recipients), self._read_message()))
                self.server.recipients.clear()
                self._reply("250 OK")
            elif verb == "QUIT":
                self._reply("221 Bye")
                return
            else:
                self._reply("250 OK")

    def _read_message(self):
        lines = []
        while True:
            line = self.rfile.readline().decode("utf-8", "replace")
            if line.strip() == ".":
                return "".join(lines)
            lines.append(line)

    def _reply(self, text):
        self.wfile.write((text + "\r\n").encode())
        self.wfile.flush()


@pytest.fixture
def smtp_server():
    server = _SMTPServer()
    _SMTPHandler.server = server
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_notification_is_delivered_to_a_real_smtp_server(smtp_server):
    # No password, so this is a plain relay: it keeps the test off the login path,
    # which the parsed-URL tests above cover.
    cfg = dict(FASTMAIL, EMAIL_PASS="", EMAIL_SMTP_HOST="localhost",
               EMAIL_SMTP_PORT=str(smtp_server.server_address[1]), EMAIL_SECURE_MODE="insecure")

    apprise_bulk.email_notify(cfg, "ARM notification", "Job 1 finished")

    # apprise sends one message per recipient, so both addresses get their own delivery
    assert len(smtp_server.received) == 2
    assert sorted(rcpttos[0] for _, rcpttos, _ in smtp_server.received) == ["one@example.com", "two@example.com"]
    for mailfrom, rcpttos, data in smtp_server.received:
        assert mailfrom == "ripper@fastmail.com"
        assert "Subject: ARM notification" in data
        assert "Job 1 finished" in data
