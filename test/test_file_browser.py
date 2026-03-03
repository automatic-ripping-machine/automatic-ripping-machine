"""Tests for the file browser service and API endpoints."""
import os
import unittest.mock

import pytest

import arm.config.config as cfg
from arm.services import file_browser


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def media_tree(tmp_path):
    """Create a realistic media directory tree and patch allowed roots."""
    raw = tmp_path / "raw"
    completed = tmp_path / "completed"
    music = tmp_path / "music"
    for d in (raw, completed, music):
        d.mkdir()

    # Create sample files and directories
    movie_dir = raw / "Serial Mom (1994)"
    movie_dir.mkdir()
    (movie_dir / "title00.mkv").write_text("fake mkv")
    (movie_dir / "title01.mkv").write_text("fake mkv 2")
    (movie_dir / "poster.jpg").write_bytes(b"\xff\xd8\xff")

    tv_dir = completed / "Breaking Bad"
    tv_dir.mkdir()
    (tv_dir / "S01E01.mp4").write_text("fake mp4")

    (music / "album.flac").write_text("fake flac")
    (music / "cover.png").write_bytes(b"\x89PNG")
    (music / "info.nfo").write_text("info")

    roots = {
        'raw': str(raw.resolve()),
        'completed': str(completed.resolve()),
        'music': str(music.resolve()),
    }

    with unittest.mock.patch.object(file_browser, 'get_allowed_roots', return_value=roots):
        yield {
            'tmp_path': tmp_path,
            'raw': raw,
            'completed': completed,
            'music': music,
            'roots': roots,
        }


# ---------------------------------------------------------------------------
# classify_file
# ---------------------------------------------------------------------------

class TestClassifyFile:
    def test_video_extensions(self):
        for ext in ('mkv', 'mp4', 'avi', 'm4v', 'ts', 'wmv', 'iso'):
            assert file_browser.classify_file(f"movie.{ext}") == 'video'

    def test_audio_extensions(self):
        for ext in ('flac', 'mp3', 'wav', 'aac', 'ogg', 'm4a'):
            assert file_browser.classify_file(f"track.{ext}") == 'audio'

    def test_image_extensions(self):
        for ext in ('jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'):
            assert file_browser.classify_file(f"image.{ext}") == 'image'

    def test_text_extensions(self):
        for ext in ('txt', 'log', 'nfo', 'srt', 'sub', 'ass'):
            assert file_browser.classify_file(f"doc.{ext}") == 'text'

    def test_archive_extensions(self):
        for ext in ('zip', 'rar', '7z', 'tar', 'gz'):
            assert file_browser.classify_file(f"file.{ext}") == 'archive'

    def test_unknown_extension(self):
        assert file_browser.classify_file("file.xyz") == 'other'

    def test_no_extension(self):
        assert file_browser.classify_file("README") == 'other'

    def test_case_insensitive(self):
        assert file_browser.classify_file("MOVIE.MKV") == 'video'


# ---------------------------------------------------------------------------
# get_roots
# ---------------------------------------------------------------------------

class TestGetRoots:
    def test_returns_configured_roots(self, media_tree):
        roots = file_browser.get_roots()
        keys = {r['key'] for r in roots}
        assert 'raw' in keys
        assert 'completed' in keys
        assert 'music' in keys

    def test_root_has_required_fields(self, media_tree):
        roots = file_browser.get_roots()
        for root in roots:
            assert 'key' in root
            assert 'label' in root
            assert 'path' in root

    def test_nonexistent_roots_excluded(self, tmp_path):
        with unittest.mock.patch.dict(cfg.arm_config, {'RAW_PATH': str(tmp_path / "nonexistent")}):
            result = file_browser.get_roots()
            # The real get_allowed_roots checks os.path.isdir, so nonexistent paths are excluded
            for r in result:
                assert r['key'] != 'raw' or os.path.isdir(r['path'])


# ---------------------------------------------------------------------------
# validate_path
# ---------------------------------------------------------------------------

class TestValidatePath:
    def test_valid_root_path(self, media_tree):
        result = file_browser.validate_path(media_tree['roots']['raw'])
        assert result.is_dir()

    def test_valid_subpath(self, media_tree):
        path = os.path.join(media_tree['roots']['raw'], "Serial Mom (1994)")
        result = file_browser.validate_path(path)
        assert result.is_dir()

    def test_valid_file_path(self, media_tree):
        path = os.path.join(media_tree['roots']['raw'], "Serial Mom (1994)", "title00.mkv")
        result = file_browser.validate_path(path)
        assert result.is_file()

    def test_traversal_attack_rejected(self, media_tree):
        attack = os.path.join(media_tree['roots']['raw'], "..", "..", "etc", "passwd")
        with pytest.raises(ValueError, match="outside allowed"):
            file_browser.validate_path(attack)

    def test_path_outside_roots_rejected(self, media_tree):
        with pytest.raises(ValueError, match="outside allowed"):
            file_browser.validate_path("/etc/passwd")

    def test_nonexistent_path_rejected(self, media_tree):
        path = os.path.join(media_tree['roots']['raw'], "nonexistent")
        with pytest.raises(FileNotFoundError):
            file_browser.validate_path(path)

    def test_symlink_escape_rejected(self, media_tree):
        # Create a symlink that escapes the root
        link = media_tree['raw'] / "escape_link"
        link.symlink_to("/etc")
        with pytest.raises(ValueError, match="outside allowed"):
            file_browser.validate_path(str(link))


# ---------------------------------------------------------------------------
# list_directory
# ---------------------------------------------------------------------------

class TestListDirectory:
    def test_list_root(self, media_tree):
        result = file_browser.list_directory(media_tree['roots']['raw'])
        assert result['path'] == media_tree['roots']['raw']
        assert result['parent'] is None
        assert len(result['entries']) == 1  # Serial Mom (1994)
        assert result['entries'][0]['name'] == 'Serial Mom (1994)'
        assert result['entries'][0]['type'] == 'directory'

    def test_list_subdirectory(self, media_tree):
        path = os.path.join(media_tree['roots']['raw'], "Serial Mom (1994)")
        result = file_browser.list_directory(path)
        assert result['parent'] == media_tree['roots']['raw']
        names = [e['name'] for e in result['entries']]
        assert 'title00.mkv' in names
        assert 'title01.mkv' in names
        assert 'poster.jpg' in names

    def test_entries_have_required_fields(self, media_tree):
        path = os.path.join(media_tree['roots']['raw'], "Serial Mom (1994)")
        result = file_browser.list_directory(path)
        for entry in result['entries']:
            assert 'name' in entry
            assert 'type' in entry
            assert 'size' in entry
            assert 'modified' in entry
            assert 'extension' in entry
            assert 'category' in entry

    def test_directories_sorted_first(self, media_tree):
        # Create a mix of files and dirs
        (media_tree['raw'] / "zzz_file.txt").write_text("text")
        (media_tree['raw'] / "aaa_dir").mkdir()
        result = file_browser.list_directory(media_tree['roots']['raw'])
        types = [e['type'] for e in result['entries']]
        # All directories should come before files
        dir_indices = [i for i, t in enumerate(types) if t == 'directory']
        file_indices = [i for i, t in enumerate(types) if t == 'file']
        if dir_indices and file_indices:
            assert max(dir_indices) < min(file_indices)

    def test_file_categories(self, media_tree):
        result = file_browser.list_directory(media_tree['roots']['music'])
        entries = {e['name']: e for e in result['entries']}
        assert entries['album.flac']['category'] == 'audio'
        assert entries['cover.png']['category'] == 'image'
        assert entries['info.nfo']['category'] == 'text'

    def test_not_a_directory(self, media_tree):
        path = os.path.join(media_tree['roots']['raw'], "Serial Mom (1994)", "title00.mkv")
        with pytest.raises(NotADirectoryError):
            file_browser.list_directory(path)

    def test_path_outside_roots(self, media_tree):
        with pytest.raises(ValueError):
            file_browser.list_directory("/etc")


# ---------------------------------------------------------------------------
# rename_item
# ---------------------------------------------------------------------------

class TestRenameItem:
    def test_rename_file(self, media_tree):
        path = os.path.join(media_tree['roots']['raw'], "Serial Mom (1994)", "title00.mkv")
        result = file_browser.rename_item(path, "main_feature.mkv")
        assert result['success'] is True
        assert "main_feature.mkv" in result['new_path']
        assert os.path.exists(result['new_path'])
        assert not os.path.exists(path)

    def test_rename_directory(self, media_tree):
        path = os.path.join(media_tree['roots']['raw'], "Serial Mom (1994)")
        result = file_browser.rename_item(path, "Serial Mom (1994) [BluRay]")
        assert result['success'] is True
        assert os.path.isdir(result['new_path'])

    def test_reject_slash_in_name(self, media_tree):
        path = os.path.join(media_tree['roots']['raw'], "Serial Mom (1994)", "title00.mkv")
        with pytest.raises(ValueError, match="must not contain"):
            file_browser.rename_item(path, "sub/file.mkv")

    def test_reject_dotdot_in_name(self, media_tree):
        path = os.path.join(media_tree['roots']['raw'], "Serial Mom (1994)", "title00.mkv")
        with pytest.raises(ValueError, match="must not contain"):
            file_browser.rename_item(path, "..hidden")

    def test_reject_empty_name(self, media_tree):
        path = os.path.join(media_tree['roots']['raw'], "Serial Mom (1994)", "title00.mkv")
        with pytest.raises(ValueError, match="cannot be empty"):
            file_browser.rename_item(path, "")

    def test_reject_existing_target(self, media_tree):
        path = os.path.join(media_tree['roots']['raw'], "Serial Mom (1994)", "title00.mkv")
        with pytest.raises(FileExistsError):
            file_browser.rename_item(path, "title01.mkv")


# ---------------------------------------------------------------------------
# move_item
# ---------------------------------------------------------------------------

class TestMoveItem:
    def test_move_file(self, media_tree):
        src = os.path.join(media_tree['roots']['raw'], "Serial Mom (1994)", "title00.mkv")
        dest = media_tree['roots']['completed']
        result = file_browser.move_item(src, dest)
        assert result['success'] is True
        assert os.path.exists(result['new_path'])
        assert not os.path.exists(src)

    def test_move_directory(self, media_tree):
        src = os.path.join(media_tree['roots']['raw'], "Serial Mom (1994)")
        dest = media_tree['roots']['completed']
        result = file_browser.move_item(src, dest)
        assert result['success'] is True
        assert os.path.isdir(result['new_path'])

    def test_reject_destination_not_dir(self, media_tree):
        src = os.path.join(media_tree['roots']['music'], "album.flac")
        dest = os.path.join(media_tree['roots']['music'], "cover.png")
        with pytest.raises(NotADirectoryError):
            file_browser.move_item(src, dest)

    def test_reject_destination_outside_roots(self, media_tree):
        src = os.path.join(media_tree['roots']['raw'], "Serial Mom (1994)", "title00.mkv")
        with pytest.raises(ValueError):
            file_browser.move_item(src, "/tmp")

    def test_reject_existing_at_destination(self, media_tree):
        # Create a file with same name in dest
        (media_tree['completed'] / "title00.mkv").write_text("existing")
        src = os.path.join(media_tree['roots']['raw'], "Serial Mom (1994)", "title00.mkv")
        dest = media_tree['roots']['completed']
        with pytest.raises(FileExistsError):
            file_browser.move_item(src, dest)


# ---------------------------------------------------------------------------
# delete_item
# ---------------------------------------------------------------------------

class TestDeleteItem:
    def test_delete_file(self, media_tree):
        path = os.path.join(media_tree['roots']['raw'], "Serial Mom (1994)", "title00.mkv")
        result = file_browser.delete_item(path)
        assert result['success'] is True
        assert not os.path.exists(path)

    def test_delete_directory(self, media_tree):
        path = os.path.join(media_tree['roots']['raw'], "Serial Mom (1994)")
        result = file_browser.delete_item(path)
        assert result['success'] is True
        assert not os.path.exists(path)

    def test_reject_root_deletion(self, media_tree):
        with pytest.raises(ValueError, match="Cannot delete a root"):
            file_browser.delete_item(media_tree['roots']['raw'])

    def test_reject_path_outside_roots(self, media_tree):
        with pytest.raises(ValueError):
            file_browser.delete_item("/etc/hosts")

    def test_reject_nonexistent(self, media_tree):
        path = os.path.join(media_tree['roots']['raw'], "ghost.mkv")
        with pytest.raises(FileNotFoundError):
            file_browser.delete_item(path)


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

class TestAPIEndpoints:
    """Test the FastAPI router endpoints via TestClient."""

    @pytest.fixture
    def client(self, media_tree):
        from fastapi.testclient import TestClient
        from arm.api.v1.files import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_get_roots(self, client, media_tree):
        resp = client.get("/api/v1/files/roots")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_directory(self, client, media_tree):
        resp = client.get("/api/v1/files/list", params={"path": media_tree['roots']['raw']})
        assert resp.status_code == 200
        data = resp.json()
        assert 'entries' in data
        assert 'path' in data

    def test_list_outside_roots_403(self, client, media_tree):
        resp = client.get("/api/v1/files/list", params={"path": "/etc"})
        assert resp.status_code == 403

    def test_list_nonexistent_404(self, client, media_tree):
        path = os.path.join(media_tree['roots']['raw'], "nonexistent")
        resp = client.get("/api/v1/files/list", params={"path": path})
        assert resp.status_code == 404

    def test_rename_success(self, client, media_tree):
        path = os.path.join(media_tree['roots']['raw'], "Serial Mom (1994)", "title00.mkv")
        resp = client.post("/api/v1/files/rename", json={"path": path, "new_name": "feature.mkv"})
        assert resp.status_code == 200
        assert resp.json()['success'] is True

    def test_rename_missing_params_400(self, client, media_tree):
        resp = client.post("/api/v1/files/rename", json={"path": "/some/path"})
        assert resp.status_code == 400

    def test_move_success(self, client, media_tree):
        path = os.path.join(media_tree['roots']['music'], "album.flac")
        dest = media_tree['roots']['completed']
        resp = client.post("/api/v1/files/move", json={"path": path, "destination": dest})
        assert resp.status_code == 200
        assert resp.json()['success'] is True

    def test_delete_success(self, client, media_tree):
        path = os.path.join(media_tree['roots']['music'], "info.nfo")
        resp = client.request("DELETE", "/api/v1/files/delete", json={"path": path})
        assert resp.status_code == 200
        assert resp.json()['success'] is True

    def test_delete_root_403(self, client, media_tree):
        resp = client.request("DELETE", "/api/v1/files/delete", json={"path": media_tree['roots']['raw']})
        assert resp.status_code == 403
