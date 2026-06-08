"""Tests for async file transfer helpers."""

import os
from pathlib import Path

import pytest

from file_transfer import async_copy, async_copy_file, async_move_file, async_rmtree


@pytest.mark.asyncio
async def test_async_copy_directory(tmp_path):
    src = tmp_path / "src_dir"
    src.mkdir()
    (src / "a.mkv").write_bytes(b"\x00" * 100)
    (src / "b.mkv").write_bytes(b"\x00" * 200)
    dst = tmp_path / "dst_dir"

    await async_copy(str(src), str(dst))

    assert (dst / "a.mkv").exists()
    assert (dst / "b.mkv").exists()
    assert (dst / "a.mkv").stat().st_size == 100
    assert (dst / "b.mkv").stat().st_size == 200
    # Source should still exist (no remove_source)
    assert src.exists()


@pytest.mark.asyncio
async def test_async_copy_directory_remove_source(tmp_path):
    src = tmp_path / "src_dir"
    src.mkdir()
    (src / "file.mkv").write_bytes(b"\x00" * 100)
    dst = tmp_path / "dst_dir"

    await async_copy(str(src), str(dst), remove_source=True)

    assert (dst / "file.mkv").exists()
    assert not src.exists()


@pytest.mark.asyncio
async def test_async_copy_file(tmp_path):
    src = tmp_path / "source.mkv"
    src.write_bytes(b"\x00" * 150)
    dst = tmp_path / "output" / "dest.mkv"

    await async_copy_file(str(src), str(dst))

    assert dst.exists()
    assert dst.stat().st_size == 150
    assert src.exists()


@pytest.mark.asyncio
async def test_async_move_file(tmp_path):
    src = tmp_path / "source.mkv"
    src.write_bytes(b"\x00" * 150)
    dst = tmp_path / "output" / "dest.mkv"

    await async_move_file(str(src), str(dst))

    assert dst.exists()
    assert dst.stat().st_size == 150
    assert not src.exists()


@pytest.mark.asyncio
async def test_async_rmtree(tmp_path):
    target = tmp_path / "to_delete"
    target.mkdir()
    (target / "sub").mkdir()
    (target / "sub" / "file.txt").write_bytes(b"data")

    await async_rmtree(str(target))

    assert not target.exists()


@pytest.mark.asyncio
async def test_async_rmtree_nonexistent(tmp_path):
    # Should not raise
    await async_rmtree(str(tmp_path / "nonexistent"))


@pytest.mark.asyncio
async def test_async_copy_nonexistent_source(tmp_path):
    with pytest.raises(FileNotFoundError):
        await async_copy(str(tmp_path / "nonexistent"), str(tmp_path / "dst"))
