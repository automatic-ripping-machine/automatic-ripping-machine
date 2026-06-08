"""Tests for gpu_monitor -- vendor-specific GPU utilization backends."""

import json
import subprocess
from unittest.mock import patch, MagicMock

import pytest

from gpu_monitor import GpuSnapshot, create_gpu_monitor


class TestGpuSnapshot:
    def test_default_values(self):
        snap = GpuSnapshot(vendor="test")
        assert snap.vendor == "test"
        assert snap.utilization_percent is None
        assert snap.memory_used_mb is None
        assert snap.memory_total_mb is None
        assert snap.temperature_c is None
        assert snap.encoder_percent is None
        assert snap.power_draw_w is None
        assert snap.power_limit_w is None
        assert snap.clock_core_mhz is None
        assert snap.clock_memory_mhz is None

    def test_to_dict(self):
        snap = GpuSnapshot(vendor="nvidia", utilization_percent=45.0, temperature_c=65.0)
        d = snap.to_dict()
        assert d["vendor"] == "nvidia"
        assert d["utilization_percent"] == pytest.approx(45.0)
        assert d["memory_used_mb"] is None
        assert d["temperature_c"] == pytest.approx(65.0)


class TestCreateGpuMonitor:
    def test_empty_vendor_returns_none(self):
        assert create_gpu_monitor("") is None

    def test_unknown_vendor_returns_none(self):
        assert create_gpu_monitor("potato") is None

    def test_nvidia_vendor(self):
        from gpu_monitor import NvidiaMonitor
        assert isinstance(create_gpu_monitor("nvidia"), NvidiaMonitor)

    def test_amd_vendor(self):
        from gpu_monitor import AmdMonitor
        assert isinstance(create_gpu_monitor("amd"), AmdMonitor)

    def test_intel_vendor(self):
        from gpu_monitor import IntelMonitor
        assert isinstance(create_gpu_monitor("intel"), IntelMonitor)

    def test_case_insensitive(self):
        from gpu_monitor import NvidiaMonitor
        assert isinstance(create_gpu_monitor("NVIDIA"), NvidiaMonitor)


class TestNvidiaMonitor:
    def test_snapshot_success(self):
        from gpu_monitor import NvidiaMonitor
        monitor = NvidiaMonitor()
        csv_output = "45, 1024, 8192, 65, 78, 180.5, 300.0, 1800, 7000\n"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = csv_output
        with patch("gpu_monitor.subprocess.run", return_value=mock_result) as mock_run:
            snap = monitor.snapshot()
            mock_run.assert_called_once()
            assert snap.vendor == "nvidia"
            assert snap.utilization_percent == pytest.approx(45.0)
            assert snap.memory_used_mb == pytest.approx(1024.0)
            assert snap.memory_total_mb == pytest.approx(8192.0)
            assert snap.temperature_c == pytest.approx(65.0)
            assert snap.encoder_percent == pytest.approx(78.0)
            assert snap.power_draw_w == pytest.approx(180.5)
            assert snap.power_limit_w == pytest.approx(300.0)
            assert snap.clock_core_mhz == pytest.approx(1800.0)
            assert snap.clock_memory_mhz == pytest.approx(7000.0)

    def test_snapshot_nvidia_smi_failure(self):
        from gpu_monitor import NvidiaMonitor
        monitor = NvidiaMonitor()
        with patch("gpu_monitor.subprocess.run", side_effect=FileNotFoundError):
            snap = monitor.snapshot()
            assert snap.vendor == "nvidia"
            assert snap.utilization_percent is None

    def test_snapshot_nvidia_smi_nonzero_exit(self):
        from gpu_monitor import NvidiaMonitor
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        with patch("gpu_monitor.subprocess.run", return_value=mock_result):
            snap = NvidiaMonitor().snapshot()
            assert snap.utilization_percent is None

    def test_snapshot_nvidia_smi_bad_csv(self):
        from gpu_monitor import NvidiaMonitor
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not,enough,fields\n"
        with patch("gpu_monitor.subprocess.run", return_value=mock_result):
            snap = NvidiaMonitor().snapshot()
            assert snap.utilization_percent is None

    def test_snapshot_nvidia_smi_timeout(self):
        from gpu_monitor import NvidiaMonitor
        with patch("gpu_monitor.subprocess.run", side_effect=subprocess.TimeoutExpired("nvidia-smi", 5)):
            snap = NvidiaMonitor().snapshot()
            assert snap.utilization_percent is None


class TestAmdMonitor:
    def _make_sysfs(self, tmp_path, gpu_busy="45", vram_used=None, vram_total=None, temp=None):
        device = tmp_path / "card0" / "device"
        device.mkdir(parents=True)
        (device / "gpu_busy_percent").write_text(gpu_busy)
        if vram_used is not None:
            (device / "mem_info_vram_used").write_text(str(vram_used))
        if vram_total is not None:
            (device / "mem_info_vram_total").write_text(str(vram_total))
        hwmon = device / "hwmon" / "hwmon0"
        hwmon.mkdir(parents=True)
        if temp is not None:
            (hwmon / "temp1_input").write_text(str(temp))
        return tmp_path

    def test_snapshot_success(self, tmp_path):
        from gpu_monitor import AmdMonitor
        sysfs = self._make_sysfs(tmp_path, gpu_busy="45", vram_used=1073741824, vram_total=8589934592, temp=65000)
        snap = AmdMonitor(sysfs_path=str(sysfs)).snapshot()
        assert snap.vendor == "amd"
        assert snap.utilization_percent == pytest.approx(45.0)
        assert snap.memory_used_mb == pytest.approx(1024.0)
        assert snap.memory_total_mb == pytest.approx(8192.0)
        assert snap.temperature_c == pytest.approx(65.0)

    def test_snapshot_no_sysfs(self):
        from gpu_monitor import AmdMonitor
        snap = AmdMonitor(sysfs_path="/nonexistent/path").snapshot()
        assert snap.vendor == "amd"
        assert snap.utilization_percent is None

    def test_snapshot_partial_sysfs(self, tmp_path):
        from gpu_monitor import AmdMonitor
        sysfs = self._make_sysfs(tmp_path, gpu_busy="80")
        snap = AmdMonitor(sysfs_path=str(sysfs)).snapshot()
        assert snap.utilization_percent == pytest.approx(80.0)
        assert snap.memory_used_mb is None
        assert snap.temperature_c is None

    def test_snapshot_bad_gpu_busy_value(self, tmp_path):
        from gpu_monitor import AmdMonitor
        sysfs = self._make_sysfs(tmp_path, gpu_busy="not_a_number")
        snap = AmdMonitor(sysfs_path=str(sysfs)).snapshot()
        assert snap.utilization_percent is None

    def test_snapshot_bad_vram_values(self, tmp_path):
        """ValueError in VRAM parsing returns None for those fields."""
        from gpu_monitor import AmdMonitor
        sysfs = self._make_sysfs(tmp_path, gpu_busy="50", vram_used="bad", vram_total="bad")
        snap = AmdMonitor(sysfs_path=str(sysfs)).snapshot()
        assert snap.utilization_percent == pytest.approx(50.0)
        assert snap.memory_used_mb is None
        assert snap.memory_total_mb is None

    def test_snapshot_bad_temp_value(self, tmp_path):
        """ValueError in temperature parsing returns None for that field."""
        from gpu_monitor import AmdMonitor
        sysfs = self._make_sysfs(tmp_path, gpu_busy="50", temp="bad")
        snap = AmdMonitor(sysfs_path=str(sysfs)).snapshot()
        assert snap.utilization_percent == pytest.approx(50.0)
        assert snap.temperature_c is None


class TestIntelMonitor:
    def test_snapshot_success(self):
        from gpu_monitor import IntelMonitor
        json_output = json.dumps({
            "period": {"duration": 1000.0, "unit": "ms"},
            "engines": {
                "Render/3D": {"busy": 12.3},
                "Blitter": {"busy": 0.0},
                "Video": {"busy": 78.5},
                "VideoEnhance": {"busy": 5.0},
            },
        }) + "\n"
        mock_proc = MagicMock()
        mock_proc.stdout.readline.return_value = json_output
        mock_proc.poll.return_value = None
        mock_proc.kill = MagicMock()
        mock_proc.wait = MagicMock()
        with patch("gpu_monitor.subprocess.Popen", return_value=mock_proc):
            snap = IntelMonitor().snapshot()
            assert snap.vendor == "intel"
            assert snap.utilization_percent == pytest.approx(12.3)
            assert snap.encoder_percent == pytest.approx(78.5)

    def test_snapshot_intel_gpu_top_missing(self):
        from gpu_monitor import IntelMonitor
        with patch("gpu_monitor.subprocess.Popen", side_effect=FileNotFoundError):
            snap = IntelMonitor().snapshot()
            assert snap.vendor == "intel"
            assert snap.utilization_percent is None

    def test_snapshot_intel_gpu_top_bad_json(self):
        from gpu_monitor import IntelMonitor
        mock_proc = MagicMock()
        mock_proc.stdout.readline.return_value = "not json\n"
        mock_proc.poll.return_value = None
        mock_proc.kill = MagicMock()
        mock_proc.wait = MagicMock()
        with patch("gpu_monitor.subprocess.Popen", return_value=mock_proc):
            snap = IntelMonitor().snapshot()
            assert snap.utilization_percent is None

    def test_snapshot_intel_gpu_top_empty_output(self):
        from gpu_monitor import IntelMonitor
        mock_proc = MagicMock()
        mock_proc.stdout.readline.return_value = ""
        mock_proc.poll.return_value = 1
        mock_proc.kill = MagicMock()
        mock_proc.wait = MagicMock()
        with patch("gpu_monitor.subprocess.Popen", return_value=mock_proc):
            snap = IntelMonitor().snapshot()
            assert snap.utilization_percent is None

    def test_snapshot_intel_gpu_top_permission_error(self):
        from gpu_monitor import IntelMonitor
        with patch("gpu_monitor.subprocess.Popen", side_effect=OSError("permission denied")):
            snap = IntelMonitor().snapshot()
            assert snap.utilization_percent is None

    def test_snapshot_intel_process_kill_oserror(self):
        """OSError during process cleanup in finally block is handled."""
        from gpu_monitor import IntelMonitor
        mock_proc = MagicMock()
        mock_proc.stdout.readline.return_value = "not json\n"
        mock_proc.kill.side_effect = OSError("no such process")
        with patch("gpu_monitor.subprocess.Popen", return_value=mock_proc):
            snap = IntelMonitor().snapshot()
            assert snap.vendor == "intel"
            mock_proc.kill.assert_called_once()
