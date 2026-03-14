"""Tests for disc type detection — README Feature: Disc Type Determination.

Covers Job.parse_udev() and Job.get_disc_type() which together determine
whether a disc is DVD, Blu-ray, music CD, data, or unknown.
Also covers DriveUtils.drives_update() drive database management.
"""
import os
import unittest.mock


class TestParseUdev:
    """Test Job.parse_udev() property extraction from udev attributes."""

    def _make_device(self, props):
        """Build a mock pyudev device that yields the given key/value pairs."""
        device = unittest.mock.MagicMock()
        device.items.return_value = list(props.items())
        return device

    def _create_job_with_udev(self, props):
        """Create a Job where parse_udev reads from the given props dict."""
        import pyudev
        from arm.models.job import Job

        device = self._make_device(props)
        with unittest.mock.patch.object(pyudev, 'Context'), \
             unittest.mock.patch.object(pyudev.Devices, 'from_device_file', return_value=device), \
             unittest.mock.patch.object(Job, 'get_pid'):
            job = Job('/dev/sr0')
        return job

    def test_bluray_detected(self):
        """ID_CDROM_MEDIA_BD sets disctype to 'bluray'."""
        job = self._create_job_with_udev({
            'ID_FS_LABEL': 'SERIAL_MOM',
            'ID_CDROM_MEDIA_BD': '1',
        })
        assert job.disctype == 'bluray'
        assert job.label == 'SERIAL_MOM'

    def test_dvd_detected(self):
        """ID_CDROM_MEDIA_DVD sets disctype to 'dvd'."""
        job = self._create_job_with_udev({
            'ID_FS_LABEL': 'MY_MOVIE',
            'ID_CDROM_MEDIA_DVD': '1',
        })
        assert job.disctype == 'dvd'

    def test_music_cd_detected(self):
        """ID_CDROM_MEDIA_TRACK_COUNT_AUDIO sets disctype to 'music'."""
        job = self._create_job_with_udev({
            'ID_CDROM_MEDIA_TRACK_COUNT_AUDIO': '12',
        })
        assert job.disctype == 'music'

    def test_data_disc_via_label(self):
        """ID_FS_LABEL of 'iso9660' sets disctype to 'data'."""
        job = self._create_job_with_udev({
            'ID_FS_LABEL': 'iso9660',
        })
        assert job.disctype == 'data'

    def test_unknown_disc(self):
        """Disc without recognized udev keys stays 'unknown'."""
        job = self._create_job_with_udev({
            'ID_VENDOR': 'SomeVendor',
        })
        assert job.disctype == 'unknown'

    def test_label_set_from_fs_label(self):
        """ID_FS_LABEL sets job.label."""
        job = self._create_job_with_udev({
            'ID_FS_LABEL': 'BACK_TO_THE_FUTURE',
            'ID_CDROM_MEDIA_DVD': '1',
        })
        assert job.label == 'BACK_TO_THE_FUTURE'

    def test_bd_takes_precedence_order(self):
        """When multiple disc type keys are present, last one seen wins."""
        # parse_udev iterates in order; both BD and DVD present
        job = self._create_job_with_udev({
            'ID_CDROM_MEDIA_DVD': '1',
            'ID_CDROM_MEDIA_BD': '1',
        })
        # BD comes after DVD in iteration → 'bluray'
        assert job.disctype == 'bluray'


class TestGetDiscType:
    """Test Job.get_disc_type() filesystem-based disc type detection."""

    def _make_job(self):
        """Create a job with mocked udev (disctype starts 'unknown')."""
        from arm.models.job import Job
        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            job = Job('/dev/sr0')
        job.disctype = 'unknown'
        job.label = 'TEST'
        return job

    def test_video_ts_detected_as_dvd(self, tmp_path):
        """Directory VIDEO_TS at mountpoint → dvd."""
        job = self._make_job()
        job.mountpoint = str(tmp_path)
        os.makedirs(tmp_path / 'VIDEO_TS')
        job.get_disc_type(False)
        assert job.disctype == 'dvd'

    def test_video_ts_lowercase(self, tmp_path):
        """Directory video_ts (lowercase) → dvd."""
        job = self._make_job()
        job.mountpoint = str(tmp_path)
        os.makedirs(tmp_path / 'video_ts')
        job.get_disc_type(False)
        assert job.disctype == 'dvd'

    def test_bdmv_detected_as_bluray(self, tmp_path):
        """Directory BDMV at mountpoint → bluray."""
        job = self._make_job()
        job.mountpoint = str(tmp_path)
        os.makedirs(tmp_path / 'BDMV')
        job.get_disc_type(False)
        assert job.disctype == 'bluray'

    def test_audio_ts_detected_as_data(self, tmp_path):
        """Non-empty AUDIO_TS directory → data (DVD-Audio)."""
        job = self._make_job()
        job.mountpoint = str(tmp_path)
        audio_dir = tmp_path / 'AUDIO_TS'
        audio_dir.mkdir()
        (audio_dir / 'dummy.aob').write_bytes(b'\x00')
        job.get_disc_type(False)
        assert job.disctype == 'data'

    def test_empty_audio_ts_not_data(self, tmp_path):
        """Empty AUDIO_TS directory does NOT trigger data detection."""
        job = self._make_job()
        job.mountpoint = str(tmp_path)
        (tmp_path / 'AUDIO_TS').mkdir()
        job.get_disc_type(False)
        # Falls through to else → 'data' (no valid dvd/bd structure)
        assert job.disctype == 'data'

    def test_no_structure_defaults_data(self, tmp_path):
        """No recognized directory structure → falls to 'data'."""
        job = self._make_job()
        job.mountpoint = str(tmp_path)
        job.get_disc_type(False)
        assert job.disctype == 'data'

    def test_hvdvd_ts_directory(self, tmp_path):
        """HVDVD_TS directory detected (HD-DVD)."""
        job = self._make_job()
        job.mountpoint = str(tmp_path)
        os.makedirs(tmp_path / 'HVDVD_TS')
        job.get_disc_type(False)
        # The code doesn't change disctype for HVDVD_TS (just comments "do something here")
        # So disctype should remain 'unknown'
        assert job.disctype == 'unknown'

    def test_music_disc_delegates_to_musicbrainz(self):
        """Music disc type delegates to music_brainz.main()."""
        job = self._make_job()
        job.disctype = 'music'
        with unittest.mock.patch('arm.ripper.music_brainz.main', return_value='Artist Title') as mock_mb:
            job.get_disc_type(False)
            mock_mb.assert_called_once_with(job)
            assert job.label == 'Artist Title'


class TestIdentifyAudioCd:
    """Test Job.identify_audio_cd() log file naming for music CDs."""

    def _make_job(self):
        from arm.models.job import Job
        with unittest.mock.patch.object(Job, 'parse_udev'), \
             unittest.mock.patch.object(Job, 'get_pid'):
            job = Job('/dev/sr0')
        job.disctype = 'music'
        job.label = ''
        job.title = ''
        job.arm_version = 'test'
        return job

    def test_identified_title_returns_label(self):
        """When MusicBrainz identifies the disc, returns the title string."""
        job = self._make_job()
        mock_discid = unittest.mock.MagicMock()
        with unittest.mock.patch('arm.ripper.music_brainz.get_disc_id', return_value=mock_discid), \
             unittest.mock.patch('arm.ripper.music_brainz.create_toc_tracks'), \
             unittest.mock.patch('arm.ripper.music_brainz.get_title', return_value='Pink Floyd Dark Side'):
            result = job.identify_audio_cd()
        assert result == 'Pink Floyd Dark Side'

    def test_unidentified_returns_music_cd(self):
        """When disc is not identified, returns 'music_cd'."""
        job = self._make_job()
        mock_discid = unittest.mock.MagicMock()
        with unittest.mock.patch('arm.ripper.music_brainz.get_disc_id', return_value=mock_discid), \
             unittest.mock.patch('arm.ripper.music_brainz.create_toc_tracks'), \
             unittest.mock.patch('arm.ripper.music_brainz.get_title', return_value='not identified'):
            result = job.identify_audio_cd()
        assert result == 'music_cd'
        assert job.label == 'not identified'
        assert job.title == 'not identified'

class TestDrivesUpdateNameless:
    """Test drives_update() handles drives with no serial_id (#1584)."""

    def _make_drive(self, mount="/dev/sr0", serial_id=None, location="",
                    maker="VirtualBox", model="CD-ROM"):
        """Create a DriveInformationMedium with optional serial_id."""
        from arm.services.drives import DriveInformationMedium
        return DriveInformationMedium(
            mount=mount,
            maker=maker,
            model=model,
            serial="",
            serial_id=serial_id,
            connection="ata",
            read_cd=True,
            read_dvd=True,
            read_bd=False,
            firmware="1.0",
            location=location,
            disc="",
            loaded=False,
            media_cd=False,
            media_dvd=False,
            media_bd=False,
        )

    def test_none_serial_id_no_crash(self, app_context):
        """A drive with no serial_id should not crash drives_update()."""
        from arm.services.drives import drives_update
        from arm.models.system_drives import SystemDrives

        drive = self._make_drive(mount="/dev/sr0", serial_id=None)
        with unittest.mock.patch('arm.services.drives.drives_search',
                                 return_value=[drive]):
            drives_update(startup=True)

        db_drive = SystemDrives.query.filter_by(mount="/dev/sr0").first()
        assert db_drive is not None
        # name should be empty string, not None
        assert db_drive.name is not None
        assert db_drive.name == ""

    def test_normal_serial_id_stored(self, app_context):
        """A drive with a normal serial_id stores it in name."""
        from arm.services.drives import drives_update
        from arm.models.system_drives import SystemDrives

        drive = self._make_drive(mount="/dev/sr0", serial_id="VBox_CD-ROM_12345")
        with unittest.mock.patch('arm.services.drives.drives_search',
                                 return_value=[drive]):
            drives_update(startup=True)

        db_drive = SystemDrives.query.filter_by(mount="/dev/sr0").first()
        assert db_drive is not None
        assert db_drive.name == "VBox_CD-ROM_12345"


class TestDrivesUpdateMatching:
    """Test drives_update() matching logic: serial_id → location → mount."""

    def _make_drive(self, mount="/dev/sr0", serial_id="", location="",
                    maker="ASUS", model="BW-16D1HT"):
        from arm.services.drives import DriveInformationMedium
        return DriveInformationMedium(
            mount=mount, maker=maker, model=model, serial="",
            serial_id=serial_id, connection="ata",
            read_cd=True, read_dvd=True, read_bd=True,
            firmware="3.10", location=location,
            disc="", loaded=False,
            media_cd=False, media_dvd=False, media_bd=False,
        )

    def _seed_drive(self, db, name, serial_id="", mount="", location=""):
        """Insert a pre-existing drive row into the DB."""
        from arm.models.system_drives import SystemDrives
        d = SystemDrives()
        d.name = name
        d.serial_id = serial_id
        d.mount = mount
        d.location = location
        d.stale = True
        db.session.add(d)
        db.session.commit()
        return d.drive_id

    # ---- Two identical drives, empty serial, different locations ----

    def test_two_empty_serial_different_locations_kept_separate(self, app_context):
        """Two drives with empty serial_id but different ID_PATH (location)
        should each keep their own DB record and custom name."""
        from arm.services.drives import drives_update
        from arm.models.system_drives import SystemDrives
        _, db = app_context

        id_a = self._seed_drive(db, name="Office Blu-ray", serial_id="",
                                mount="/dev/sr0",
                                location="pci-0000:00:1f.2-ata-1")
        id_b = self._seed_drive(db, name="Bedroom Blu-ray", serial_id="",
                                mount="/dev/sr1",
                                location="pci-0000:00:1f.2-ata-2")

        scan = [
            self._make_drive(mount="/dev/sr0", serial_id="",
                             location="pci-0000:00:1f.2-ata-1"),
            self._make_drive(mount="/dev/sr1", serial_id="",
                             location="pci-0000:00:1f.2-ata-2"),
        ]
        with unittest.mock.patch('arm.services.drives.drives_search',
                                 return_value=scan):
            drives_update(startup=True)

        a = SystemDrives.query.get(id_a)
        b = SystemDrives.query.get(id_b)
        assert a.name == "Office Blu-ray"
        assert b.name == "Bedroom Blu-ray"
        assert a.mount == "/dev/sr0"
        assert b.mount == "/dev/sr1"
        assert not a.stale
        assert not b.stale

    def test_two_empty_serial_swap_mount_points(self, app_context):
        """Two drives with empty serial_id swap /dev/sr0 ↔ /dev/sr1 after
        reboot. Location fallback should track the physical drive."""
        from arm.services.drives import drives_update
        from arm.models.system_drives import SystemDrives
        _, db = app_context

        id_a = self._seed_drive(db, name="Office Blu-ray", serial_id="",
                                mount="/dev/sr0",
                                location="pci-0000:00:1f.2-ata-1")
        id_b = self._seed_drive(db, name="Bedroom Blu-ray", serial_id="",
                                mount="/dev/sr1",
                                location="pci-0000:00:1f.2-ata-2")

        # Mounts swapped — sr0 is now on ata-2, sr1 on ata-1
        scan = [
            self._make_drive(mount="/dev/sr0", serial_id="",
                             location="pci-0000:00:1f.2-ata-2"),
            self._make_drive(mount="/dev/sr1", serial_id="",
                             location="pci-0000:00:1f.2-ata-1"),
        ]
        with unittest.mock.patch('arm.services.drives.drives_search',
                                 return_value=scan):
            drives_update(startup=True)

        a = SystemDrives.query.get(id_a)
        b = SystemDrives.query.get(id_b)
        # Names follow the physical drive (location), not the mount path
        assert a.name == "Office Blu-ray"
        assert a.location == "pci-0000:00:1f.2-ata-1"
        assert a.mount == "/dev/sr1"  # mount updated to new path
        assert b.name == "Bedroom Blu-ray"
        assert b.location == "pci-0000:00:1f.2-ata-2"
        assert b.mount == "/dev/sr0"

    def test_serial_match_beats_location(self, app_context):
        """When serial_id is populated, it takes priority over location."""
        from arm.services.drives import drives_update
        from arm.models.system_drives import SystemDrives
        _, db = app_context

        id_a = self._seed_drive(db, name="My Drive", serial_id="ASUS_BW_ABC123",
                                mount="/dev/sr0",
                                location="pci-0000:00:1f.2-ata-1")

        # Same serial, but location changed (physically moved to different port)
        scan = [
            self._make_drive(mount="/dev/sr0", serial_id="ASUS_BW_ABC123",
                             location="pci-0000:03:00.0-ata-1"),
        ]
        with unittest.mock.patch('arm.services.drives.drives_search',
                                 return_value=scan):
            drives_update(startup=True)

        a = SystemDrives.query.get(id_a)
        assert a.name == "My Drive"
        assert a.serial_id == "ASUS_BW_ABC123"
        # Location updated to new port
        assert a.location == "pci-0000:03:00.0-ata-1"

    def test_empty_serial_empty_location_falls_to_mount(self, app_context):
        """With no serial_id and no location, mount path is the last resort."""
        from arm.services.drives import drives_update
        from arm.models.system_drives import SystemDrives
        _, db = app_context

        id_a = self._seed_drive(db, name="VM Drive", serial_id="",
                                mount="/dev/sr0", location="")

        scan = [
            self._make_drive(mount="/dev/sr0", serial_id="", location=""),
        ]
        with unittest.mock.patch('arm.services.drives.drives_search',
                                 return_value=scan):
            drives_update(startup=True)

        a = SystemDrives.query.get(id_a)
        assert a.name == "VM Drive"
        assert a.mount == "/dev/sr0"
        assert not a.stale

    def test_three_identical_drives_all_empty_serial(self, app_context):
        """Three identical drives, all with empty serial_id but unique
        locations, should each preserve their custom name."""
        from arm.services.drives import drives_update
        from arm.models.system_drives import SystemDrives
        _, db = app_context

        ids = []
        for i, (name, loc) in enumerate([
            ("Drive A", "pci-0000:00:1f.2-ata-1"),
            ("Drive B", "pci-0000:00:1f.2-ata-2"),
            ("Drive C", "pci-0000:00:1f.2-ata-3"),
        ]):
            ids.append(self._seed_drive(
                db, name=name, serial_id="",
                mount=f"/dev/sr{i}", location=loc,
            ))

        scan = [
            self._make_drive(mount=f"/dev/sr{i}", serial_id="",
                             location=loc)
            for i, (_, loc) in enumerate([
                ("Drive A", "pci-0000:00:1f.2-ata-1"),
                ("Drive B", "pci-0000:00:1f.2-ata-2"),
                ("Drive C", "pci-0000:00:1f.2-ata-3"),
            ])
        ]
        with unittest.mock.patch('arm.services.drives.drives_search',
                                 return_value=scan):
            drives_update(startup=True)

        for drive_id, expected_name in zip(ids, ["Drive A", "Drive B", "Drive C"]):
            d = SystemDrives.query.get(drive_id)
            assert d.name == expected_name, f"drive_id={drive_id} expected '{expected_name}' got '{d.name}'"
            assert not d.stale

    def test_new_drive_gets_created(self, app_context):
        """A drive with unknown serial_id and location creates a new record."""
        from arm.services.drives import drives_update
        from arm.models.system_drives import SystemDrives
        _, _ = app_context

        scan = [
            self._make_drive(mount="/dev/sr0", serial_id="NEW_DRIVE_XYZ",
                             location="pci-0000:05:00.0-usb-0:1"),
        ]
        with unittest.mock.patch('arm.services.drives.drives_search',
                                 return_value=scan):
            drives_update(startup=True)

        d = SystemDrives.query.filter_by(serial_id="NEW_DRIVE_XYZ").first()
        assert d is not None
        assert d.mount == "/dev/sr0"
        assert d.location == "pci-0000:05:00.0-usb-0:1"

    def test_custom_name_survives_mount_swap_with_serial(self, app_context):
        """Drive with valid serial_id preserves custom name even when mount
        path changes."""
        from arm.services.drives import drives_update
        from arm.models.system_drives import SystemDrives
        _, db = app_context

        id_a = self._seed_drive(db, name="Living Room Blu-ray",
                                serial_id="LG_WH16NS40_SN111",
                                mount="/dev/sr0",
                                location="pci-0000:00:1f.2-ata-1")
        id_b = self._seed_drive(db, name="Garage DVD",
                                serial_id="LG_WH16NS40_SN222",
                                mount="/dev/sr1",
                                location="pci-0000:00:1f.2-ata-2")

        # sr0 ↔ sr1 swapped
        scan = [
            self._make_drive(mount="/dev/sr0", serial_id="LG_WH16NS40_SN222",
                             location="pci-0000:00:1f.2-ata-2"),
            self._make_drive(mount="/dev/sr1", serial_id="LG_WH16NS40_SN111",
                             location="pci-0000:00:1f.2-ata-1"),
        ]
        with unittest.mock.patch('arm.services.drives.drives_search',
                                 return_value=scan):
            drives_update(startup=True)

        a = SystemDrives.query.get(id_a)
        b = SystemDrives.query.get(id_b)
        assert a.name == "Living Room Blu-ray"
        assert a.mount == "/dev/sr1"
        assert b.name == "Garage DVD"
        assert b.mount == "/dev/sr0"
