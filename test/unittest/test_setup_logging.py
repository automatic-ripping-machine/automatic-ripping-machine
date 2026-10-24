"""Setup-phase ripper messages reach arm.log."""

import logging


def test_setup_messages_logged_through_the_root_logger_reach_arm_log(tmp_path, monkeypatch):
    import arm.config.config as cfg
    from arm.ripper import logger

    monkeypatch.setitem(cfg.arm_config, "LOGPATH", str(tmp_path))
    root = logging.getLogger()
    before, level = list(root.handlers), root.level
    try:
        logger.create_early_logger(stdout=False, syslog=False)
        # The ripper logs with logging.info() etc. (the root logger), e.g. "No job started".
        logging.warning("No job started: probe-message")
        for handler in root.handlers:
            handler.flush()
    finally:
        for handler in [h for h in root.handlers if h not in before]:
            root.removeHandler(handler)
            handler.close()
        root.setLevel(level)
    assert "probe-message" in (tmp_path / "arm.log").read_text()
