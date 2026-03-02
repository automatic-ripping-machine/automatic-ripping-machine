"""Tests for json_api pure-logic functions (arm/services/jobs.py)."""
import datetime

import pytest


class TestPercentage:
    """Test percentage() calculation."""

    def test_half(self):
        from arm.services.jobs import percentage

        assert abs(percentage(50, 100) - 50.0) < 0.01

    def test_full(self):
        from arm.services.jobs import percentage

        assert abs(percentage(100, 100) - 100.0) < 0.01

    def test_zero_part(self):
        from arm.services.jobs import percentage

        assert abs(percentage(0, 100)) < 0.01

    def test_string_inputs(self):
        from arm.services.jobs import percentage

        # Function uses float() cast, should handle string numbers
        assert abs(percentage("50", "200") - 25.0) < 0.01

    def test_zero_whole_raises(self):
        from arm.services.jobs import percentage

        with pytest.raises(ZeroDivisionError):
            percentage(50, 0)

    def test_fractional(self):
        from arm.services.jobs import percentage

        result = percentage(1, 3)
        assert abs(result - 33.33) < 0.01


class TestCalcProcessTime:
    """Test calc_process_time() ETA estimation."""

    def test_basic_eta(self, app_context):
        from arm.services.jobs import calc_process_time

        start = datetime.datetime.now() - datetime.timedelta(minutes=10)
        result = calc_process_time(start, 5, 10)
        # Should return a string with "- @HH:MM:SS" format
        assert isinstance(result, str)
        assert "@" in result

    def test_type_error_handled(self, app_context):
        from arm.services.jobs import calc_process_time

        # Passing None as starttime triggers TypeError
        result = calc_process_time(None, 5, 10)
        # Should not raise, returns a string
        assert isinstance(result, str)

    def test_zero_iteration_handled(self, app_context):
        from arm.services.jobs import calc_process_time

        start = datetime.datetime.now() - datetime.timedelta(minutes=5)
        # cur_iter=0 should not raise — returns graceful fallback string
        result = calc_process_time(start, 0, 10)
        assert isinstance(result, str)
        assert "@" in result

    def test_non_numeric_iteration_handled(self, app_context):
        """Non-numeric cur_iter (e.g. from abcde log parsing) should not raise (#1641)."""
        from arm.services.jobs import calc_process_time

        start = datetime.datetime.now() - datetime.timedelta(minutes=5)
        result = calc_process_time(start, "not_a_number", 10)
        assert isinstance(result, str)
        assert "@" in result


class TestReadNotification:
    """Test read_notification() marking."""

    def test_read_existing_notification(self, app_context):
        from arm.services.jobs import read_notification
        from arm.models.notifications import Notifications
        from arm.database import db

        notif = Notifications("Test Title", "Test message")
        db.session.add(notif)
        db.session.commit()

        result = read_notification(notif.id)
        assert result['success'] is True

    def test_read_nonexistent_notification(self, app_context):
        from arm.services.jobs import read_notification

        result = read_notification(99999)
        assert result['success'] is False
        assert "not found" in result['message'].lower() or "already read" in result['message'].lower()


class TestGetNotifyTimeout:
    """Test get_notify_timeout() setting retrieval."""

    def test_no_settings_returns_default(self, app_context):
        from arm.services.jobs import get_notify_timeout

        result = get_notify_timeout(None)
        assert result['success'] is True
        assert result['notify_timeout'] == '6500'

    def test_with_settings(self, app_context):
        from arm.services.jobs import get_notify_timeout
        from arm.models.ui_settings import UISettings
        from arm.database import db

        settings = UISettings(notify_refresh=5000)
        db.session.add(settings)
        db.session.commit()

        result = get_notify_timeout(None)
        assert result['success'] is True
        assert result['notify_timeout'] == 5000


class TestGetNotifications:
    """Test get_notifications() list retrieval."""

    def test_empty_returns_list(self, app_context):
        from arm.services.jobs import get_notifications

        result = get_notifications()
        assert isinstance(result, list)
        assert len(result) == 0

    def test_returns_unseen(self, app_context):
        from arm.services.jobs import get_notifications
        from arm.models.notifications import Notifications
        from arm.database import db

        n1 = Notifications("Unseen", "body1")
        n2 = Notifications("Also unseen", "body2")
        db.session.add_all([n1, n2])
        db.session.commit()

        result = get_notifications()
        assert len(result) == 2

    def test_excludes_seen(self, app_context):
        from arm.services.jobs import get_notifications
        from arm.models.notifications import Notifications
        from arm.database import db

        n1 = Notifications("Unseen", "body1")
        n2 = Notifications("Seen", "body2")
        n2.seen = True
        db.session.add_all([n1, n2])
        db.session.commit()

        result = get_notifications()
        assert len(result) == 1
