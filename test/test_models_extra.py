"""Tests for model classes: AppState and SystemInfo."""
import platform
import unittest.mock

import pytest


class TestAppState:
    """Test AppState singleton model."""

    def test_get_creates_singleton(self, app_context):
        from arm.models.app_state import AppState
        state = AppState.get()
        assert state is not None
        assert state.id == 1
        assert state.ripping_paused is False

    def test_get_returns_existing(self, app_context):
        from arm.models.app_state import AppState
        from arm.database import db
        existing = AppState(id=1, ripping_paused=True)
        db.session.add(existing)
        db.session.commit()

        state = AppState.get()
        assert state.ripping_paused is True

    def test_get_idempotent(self, app_context):
        from arm.models.app_state import AppState
        state1 = AppState.get()
        state2 = AppState.get()
        assert state1.id == state2.id

    def test_repr(self, app_context):
        from arm.models.app_state import AppState
        state = AppState(id=1, ripping_paused=False)
        assert "ripping_paused=False" in repr(state)

    def test_repr_paused(self, app_context):
        from arm.models.app_state import AppState
        state = AppState(id=1, ripping_paused=True)
        assert "ripping_paused=True" in repr(state)

    def test_toggle_state(self, app_context):
        from arm.models.app_state import AppState
        from arm.database import db
        state = AppState.get()
        assert state.ripping_paused is False
        state.ripping_paused = True
        db.session.commit()
        refreshed = AppState.get()
        assert refreshed.ripping_paused is True


class TestSystemInfo:
    """Test SystemInfo model."""

    def test_init_sets_name_and_description(self, app_context):
        from arm.models.system_info import SystemInfo
        with unittest.mock.patch.object(SystemInfo, 'get_cpu_info'), \
             unittest.mock.patch.object(SystemInfo, 'get_memory'):
            si = SystemInfo(name="Test Server", description="My server")
        assert si.name == "Test Server"
        assert si.description == "My server"

    def test_default_name_and_description(self, app_context):
        from arm.models.system_info import SystemInfo
        with unittest.mock.patch.object(SystemInfo, 'get_cpu_info'), \
             unittest.mock.patch.object(SystemInfo, 'get_memory'):
            si = SystemInfo()
        assert si.name == "ARM Server"
        assert si.description == "Automatic Ripping Machine main server"

    def test_get_cpu_info_linux(self, app_context):
        from arm.models.system_info import SystemInfo
        cpu_output = b"model name\t: AMD Ryzen 5 3600 6-Core Processor\n"
        with unittest.mock.patch("arm.models.system_info.platform.system",
                                 return_value="Linux"), \
             unittest.mock.patch("arm.models.system_info.subprocess.check_output",
                                 return_value=cpu_output), \
             unittest.mock.patch.object(SystemInfo, 'get_memory'):
            si = SystemInfo()
        assert "Ryzen" in si.cpu

    def test_get_cpu_info_windows(self, app_context):
        from arm.models.system_info import SystemInfo
        with unittest.mock.patch("arm.models.system_info.platform.system",
                                 return_value="Windows"), \
             unittest.mock.patch("arm.models.system_info.platform.processor",
                                 return_value="Intel64 Family 6"), \
             unittest.mock.patch.object(SystemInfo, 'get_memory'):
            si = SystemInfo()
        assert si.cpu == "Intel64 Family 6"

    def test_get_cpu_info_no_match(self, app_context):
        from arm.models.system_info import SystemInfo
        # Linux but cpuinfo doesn't contain model name
        with unittest.mock.patch("arm.models.system_info.platform.system",
                                 return_value="Linux"), \
             unittest.mock.patch("arm.models.system_info.subprocess.check_output",
                                 return_value=b"processor\t: 0\n"), \
             unittest.mock.patch.object(SystemInfo, 'get_memory'):
            si = SystemInfo()
        assert si.cpu == "Unable to Identify"

    def test_get_memory(self, app_context):
        from arm.models.system_info import SystemInfo
        mock_mem = unittest.mock.MagicMock()
        mock_mem.total = 17179869184  # 16 GB
        with unittest.mock.patch.object(SystemInfo, 'get_cpu_info'), \
             unittest.mock.patch("arm.models.system_info.psutil.virtual_memory",
                                 return_value=mock_mem):
            si = SystemInfo()
            si.get_memory()
        assert si.mem_total == pytest.approx(16.0)

    def test_get_memory_failure(self, app_context):
        from arm.models.system_info import SystemInfo
        with unittest.mock.patch.object(SystemInfo, 'get_cpu_info'), \
             unittest.mock.patch("arm.models.system_info.psutil.virtual_memory",
                                 side_effect=EnvironmentError("no mem")):
            si = SystemInfo()
            si.get_memory()
        assert si.mem_total == 0

    def test_get_cpu_info_darwin(self, app_context):
        from arm.models.system_info import SystemInfo
        with unittest.mock.patch("arm.models.system_info.platform.system",
                                 return_value="Darwin"), \
             unittest.mock.patch("arm.models.system_info.subprocess.check_output",
                                 return_value=b"Apple M1 Pro"), \
             unittest.mock.patch.object(SystemInfo, 'get_memory'):
            si = SystemInfo()
        assert si.cpu == b"Apple M1 Pro"
