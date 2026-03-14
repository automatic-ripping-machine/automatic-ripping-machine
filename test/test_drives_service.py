"""Tests for arm/services/drives.py — drive management service."""
import unittest.mock

import pytest


class TestDriveInformation:
    """Test DriveInformation dataclass."""

    def test_decode_encoded_string(self):
        from arm.services.drives import DriveInformation
        di = DriveInformation(
            mount="/dev/sr0",
            maker="Pioneer\\x20Corp",
            model="BD-RW\\x20BDR-S12J",
            serial="ABC123",
            serial_id="Pioneer_BDR-S12J_ABC123",
        )
        assert di.maker == "Pioneer Corp"
        assert di.model == "BD-RW BDR-S12J"

    def test_decode_none_value(self):
        from arm.services.drives import DriveInformation
        di = DriveInformation(
            mount="/dev/sr0",
            maker=None,
            model=None,
            serial="ABC",
            serial_id="id",
        )
        assert di.maker == ""
        assert di.model == ""

    def test_ordering(self):
        from arm.services.drives import DriveInformation
        di1 = DriveInformation("/dev/sr0", "A", "B", "C", "D")
        di2 = DriveInformation("/dev/sr1", "A", "B", "C", "D")
        assert di1 < di2


class TestDriveInformationExtended:
    """Test DriveInformationExtended dataclass."""

    def test_convert_bool_values(self):
        from arm.services.drives import DriveInformationExtended
        die = DriveInformationExtended(
            mount="/dev/sr0", maker="A", model="B", serial="C", serial_id="D",
            connection="usb", read_cd="1", read_dvd="1", read_bd="0",
            firmware="1.0", location="/sys/bus/usb/1",
        )
        assert die.read_cd is True
        assert die.read_dvd is True
        assert die.read_bd is False

    def test_convert_bool_none(self):
        from arm.services.drives import DriveInformationExtended
        die = DriveInformationExtended(
            mount="/dev/sr0", maker="A", model="B", serial="C", serial_id="D",
            connection="ata", read_cd=None, read_dvd="unknown", read_bd="",
            firmware="1.0", location="",
        )
        assert die.read_cd is False
        assert die.read_dvd is False
        assert die.read_bd is False

    def test_convert_bool_invalid(self):
        from arm.services.drives import DriveInformationExtended
        die = DriveInformationExtended(
            mount="/dev/sr0", maker="A", model="B", serial="C", serial_id="D",
            connection="ata", read_cd="not_a_number", read_dvd="1", read_bd="1",
            firmware="1.0", location="",
        )
        assert die.read_cd is False


class TestDriveInformationMedium:
    """Test DriveInformationMedium dataclass."""

    def test_medium_fields(self):
        from arm.services.drives import DriveInformationMedium
        dim = DriveInformationMedium(
            mount="/dev/sr0", maker="A", model="B", serial="C", serial_id="D",
            connection="usb", read_cd="1", read_dvd="1", read_bd="1",
            firmware="1.0", location="/sys/bus/usb/1",
            disc="MY_DISC", loaded="1", media_cd="0", media_dvd="0", media_bd="1",
        )
        assert dim.disc == "MY_DISC"
        assert dim.loaded is True
        assert dim.media_cd is False
        assert dim.media_bd is True

    def test_masked_repr(self):
        from arm.services.drives import DriveInformationMedium
        dim = DriveInformationMedium(
            mount="/dev/sr0", maker="A", model="B", serial="ABCDEFGHIJ", serial_id="D",
            connection="usb", read_cd="1", read_dvd="1", read_bd="1",
            firmware="1.0", location="",
            disc="DISC", loaded="1", media_cd="0", media_dvd="1", media_bd="0",
        )
        r = repr(dim)
        # Serial should be masked (last 6 chars replaced with asterisks)
        assert "ABCDEFGHIJ" not in r
        assert "ABCD******" in r

    def test_masked_repr_short_serial(self):
        from arm.services.drives import DriveInformationMedium
        dim = DriveInformationMedium(
            mount="/dev/sr0", maker="A", model="B", serial="AB", serial_id="D",
            connection="usb", read_cd="1", read_dvd="1", read_bd="1",
            firmware="1.0", location="",
            disc="DISC", loaded="0", media_cd="0", media_dvd="0", media_bd="0",
        )
        r = repr(dim)
        assert "AB" not in r
        assert "**" in r


class TestFindOrCreateDrive:
    """Test _find_or_create_drive()."""

    def test_find_by_serial_id(self, app_context):
        from arm.services.drives import _find_or_create_drive, DriveInformation
        from arm.models import SystemDrives
        from arm.database import db

        db_drive = SystemDrives()
        db_drive.serial_id = "Pioneer_BDR_ABC"
        db_drive.stale = True
        db_drive.mount = "/dev/sr0"
        db.session.add(db_drive)
        db.session.commit()

        drive = DriveInformation(
            mount="/dev/sr0", maker="Pioneer", model="BDR",
            serial="ABC", serial_id="Pioneer_BDR_ABC",
        )
        result = _find_or_create_drive(drive)
        assert result.serial_id == "Pioneer_BDR_ABC"

    def test_find_by_mount(self, app_context):
        from arm.services.drives import _find_or_create_drive, DriveInformationMedium
        from arm.models import SystemDrives
        from arm.database import db

        db_drive = SystemDrives()
        db_drive.serial_id = "old_serial"
        db_drive.stale = False
        db_drive.mount = "/dev/sr0"
        db.session.add(db_drive)
        db.session.commit()

        drive = DriveInformationMedium(
            mount="/dev/sr0", maker="A", model="B",
            serial="C", serial_id="new_serial",
            connection="ata", read_cd="1", read_dvd="1", read_bd="0",
            firmware="1.0", location="",
            disc="DISC", loaded="0", media_cd="0", media_dvd="0", media_bd="0",
        )
        result = _find_or_create_drive(drive)
        assert result.mount == "/dev/sr0"

    def test_create_new_drive(self, app_context):
        from arm.services.drives import _find_or_create_drive, DriveInformationMedium
        from arm.models import SystemDrives
        from arm.database import db

        drive = DriveInformationMedium(
            mount="/dev/sr1", maker="LG", model="WH16",
            serial="XYZ", serial_id="LG_WH16_XYZ",
            connection="usb", read_cd="1", read_dvd="1", read_bd="1",
            firmware="2.0", location="/sys/bus/usb/2",
            disc="", loaded="0", media_cd="0", media_dvd="0", media_bd="0",
        )
        result = _find_or_create_drive(drive)
        assert result.name == "LG_WH16_XYZ"


class TestJobCleanup:
    """Test job_cleanup() and clear_drive_job()."""

    def test_job_cleanup(self, app_context):
        from arm.services.drives import job_cleanup
        from arm.models import SystemDrives
        from arm.database import db

        d = SystemDrives()
        d.mount = "/dev/sr0"
        d.job_id_current = 42
        d.job_id_previous = None
        db.session.add(d)
        db.session.commit()

        job_cleanup(42)
        db.session.refresh(d)
        assert d.job_id_current is None

    def test_job_cleanup_previous(self, app_context):
        from arm.services.drives import job_cleanup
        from arm.models import SystemDrives
        from arm.database import db

        d = SystemDrives()
        d.mount = "/dev/sr0"
        d.job_id_current = None
        d.job_id_previous = 99
        db.session.add(d)
        db.session.commit()

        job_cleanup(99)
        db.session.refresh(d)
        assert d.job_id_previous is None

    def test_clear_drive_job_alias(self, app_context):
        from arm.services.drives import clear_drive_job, job_cleanup
        assert clear_drive_job is not None
        # Just verify it's callable
        from arm.models import SystemDrives
        from arm.database import db
        d = SystemDrives()
        d.mount = "/dev/sr0"
        d.job_id_current = 10
        db.session.add(d)
        db.session.commit()
        clear_drive_job(10)
        db.session.refresh(d)
        assert d.job_id_current is None


class TestGetDrives:
    """Test get_drives() wrapper."""

    def test_returns_list(self, app_context):
        from arm.services.drives import get_drives
        from arm.models import SystemDrives
        from arm.database import db

        d = SystemDrives()
        d.mount = "/dev/sr0"
        d.name = "Test"
        db.session.add(d)
        db.session.commit()

        result = get_drives()
        assert len(result) == 1
        assert result[0].mount == "/dev/sr0"

    def test_returns_empty(self, app_context):
        from arm.services.drives import get_drives
        result = get_drives()
        assert result == []


class TestUpdateDriveJob:
    """Test update_drive_job()."""

    def test_update_job_for_known_drive(self, app_context):
        from arm.services.drives import update_drive_job
        from arm.models import SystemDrives
        from arm.database import db

        d = SystemDrives()
        d.mount = "/dev/sr0"
        d.name = "Test"
        db.session.add(d)
        db.session.commit()

        job = unittest.mock.MagicMock()
        job.devpath = "/dev/sr0"
        job.job_id = 42

        update_drive_job(job)
        db.session.refresh(d)
        assert d.job_id_current == 42

    def test_update_job_no_matching_drive(self, app_context):
        from arm.services.drives import update_drive_job
        job = unittest.mock.MagicMock()
        job.devpath = "/dev/sr99"
        job.job_id = 1
        # Should not raise, just log a warning
        update_drive_job(job)


class TestDrivesUpdate:
    """Test drives_update() orchestration."""

    def test_marks_drives_stale_and_rescans(self, app_context):
        from arm.services.drives import drives_update
        from arm.models import SystemDrives
        from arm.database import db

        d = SystemDrives()
        d.mount = "/dev/sr0"
        d.name = "Test"
        d.stale = False
        d.job_id_current = None  # processing is a property: job_current is not None
        db.session.add(d)
        db.session.commit()

        with unittest.mock.patch("arm.services.drives.drives_search", return_value=[]):
            result = drives_update()
        # Drive should have been cleaned up (mount blanked)
        db.session.refresh(d)
        assert d.mount == ""

    def test_startup_retry_on_no_drives(self, app_context):
        from arm.services.drives import drives_update
        from arm.models import SystemDrives
        from arm.database import db

        call_count = 0

        def mock_search():
            nonlocal call_count
            call_count += 1
            return iter([])

        with unittest.mock.patch("arm.services.drives.drives_search",
                                 side_effect=mock_search), \
             unittest.mock.patch("arm.services.drives.time.sleep"):
            drives_update(startup=True)
        # Should retry 3 times + initial = 4 calls
        assert call_count == 4

    def test_active_drive_not_marked_stale(self, app_context, sample_job):
        from arm.services.drives import drives_update
        from arm.models import SystemDrives
        from arm.database import db

        d = SystemDrives()
        d.mount = "/dev/sr0"
        d.name = "Active"
        d.stale = False
        d.job_id_current = sample_job.job_id  # makes processing=True
        db.session.add(d)
        db.session.commit()

        with unittest.mock.patch("arm.services.drives.drives_search", return_value=[]):
            drives_update()
        db.session.refresh(d)
        # Active drive should NOT have stale=True
        assert d.stale is False


class TestCleanupStaleDrives:
    """Test _cleanup_stale_drives()."""

    def test_cleans_stale_non_processing(self, app_context):
        from arm.services.drives import _cleanup_stale_drives
        from arm.models import SystemDrives
        from arm.database import db

        d = SystemDrives()
        d.mount = "/dev/sr0"
        d.stale = True
        d.job_id_current = None  # processing = False
        db.session.add(d)
        db.session.commit()

        count = _cleanup_stale_drives()
        assert count == 1
        db.session.refresh(d)
        assert d.mount == ""

    def test_keeps_stale_processing(self, app_context, sample_job):
        from arm.services.drives import _cleanup_stale_drives
        from arm.models import SystemDrives
        from arm.database import db

        d = SystemDrives()
        d.mount = "/dev/sr0"
        d.stale = True
        d.job_id_current = sample_job.job_id  # processing = True
        db.session.add(d)
        db.session.commit()

        count = _cleanup_stale_drives()
        assert count == 0
        db.session.refresh(d)
        # Stale flag should be cleared for active drives
        assert d.stale is False
