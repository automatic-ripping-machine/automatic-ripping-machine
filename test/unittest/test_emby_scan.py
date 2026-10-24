"""Emby scan: a refused connection never fails a finished rip."""


def test_unreachable_emby_server_is_logged_not_raised(monkeypatch):
    import requests
    import arm.config.config as cfg
    from arm.ripper import utils

    for key, value in {"EMBY_REFRESH": True, "EMBY_SERVER": "127.0.0.1", "EMBY_PORT": 9,
                       "EMBY_API_KEY": "unused"}.items():
        monkeypatch.setitem(cfg.arm_config, key, value)
    calls = []

    def post(url, **kwargs):
        calls.append(kwargs)
        raise requests.exceptions.ConnectionError("refused")

    monkeypatch.setattr(utils.requests, "post", post)
    utils.scan_emby()
    assert len(calls) == 1
    assert calls[0].get("timeout")
