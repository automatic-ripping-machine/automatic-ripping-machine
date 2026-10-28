"""abcde completion and per-invocation output verification (#1526)."""

from concurrent.futures import ThreadPoolExecutor
import os
import stat
from types import SimpleNamespace

import pytest

ABCDE = r'''#!/bin/bash
OUTPUTTYPE=ogg
OUTPUTDIR="$FAKE_ABCDE_OUT"
run_command () { shift; "$@"; }
while getopts 'd:c:' opt; do
    case "$opt" in
        d) device="${OPTARG##*/}" ;;
        c) config="$OPTARG" ;;
    esac
done
. "$config"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
mode="$FAKE_ABCDE_MODE"
count=3
[[ "$mode" == short ]] && count=2
for TMPOUTPUT in ${OUTPUTTYPE//,/ }; do
    extension="$TMPOUTPUT"
    [[ "$extension" == vorbis ]] && extension=ogg
    [[ "$extension" == flac && -n "$FLACOUTPUTCONTAINER" ]] && extension="$FLACOUTPUTCONTAINER"
    mkdir -p "$OUTPUTDIR/Artist/$device"
    for ((n=1; n<=count; n++)); do
        source="$work/$n.$extension"
        printf audio > "$source"
        [[ "$mode" == empty && "$n" == 2 ]] && : > "$source"
        [[ "$mode" == movefail && "$n" == 2 ]] && rm "$source"
        run_command "movetrack-$n" mv "$source" "$OUTPUTDIR/Artist/$device/$n.$extension"
    done
done
if [[ -n "$FAKE_ABCDE_BARRIER" ]]; then
    touch "$FAKE_ABCDE_BARRIER/$device"
    for ((n=0; n<100; n++)); do
        [[ -f "$FAKE_ABCDE_BARRIER/sr0" && -f "$FAKE_ABCDE_BARRIER/sr1" ]] && break
        sleep 0.02
    done
    [[ "$n" == 100 ]] && exit 4
fi
[[ "$mode" == unfinished ]] || echo "Finished."
[[ "$mode" == exit ]] && exit 3
exit 0
'''


@pytest.fixture
def abcde(tmp_path, monkeypatch):
    import arm.config.config as cfg
    from arm.ripper import music_brainz, utils

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "abcde"
    script.write_text(ABCDE)
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("FAKE_ABCDE_OUT", str(tmp_path / "music"))
    conf = tmp_path / "abcde.conf"
    conf.write_text('OUTPUTTYPE=flac\nOUTPUTDIR="%s"\n' % (tmp_path / "music"))
    monkeypatch.setitem(cfg.arm_config, "ABCDE_CONFIG_FILE", str(conf))
    monkeypatch.setattr(music_brainz, "get_disc_id", lambda job: SimpleNamespace(tracks=[1, 2, 3]))
    updates = []
    monkeypatch.setattr(utils, "database_updater", lambda values, job: updates.append(values))

    def run(mode, device="sr0"):
        monkeypatch.setenv("FAKE_ABCDE_MODE", mode)
        job = SimpleNamespace(disctype="music", devpath="/dev/" + device,
                              config=SimpleNamespace(LOGPATH=str(tmp_path)))
        return utils.rip_music(job, device + ".log")

    return run, updates, conf


def test_complete_rip_succeeds(abcde):
    run, updates, _ = abcde
    assert run("ok") is True
    assert updates[-1] == {"status": "active"}


@pytest.mark.parametrize("mode,reason", [("unfinished", "Finished"), ("short", "2 flac file"),
                                         ("empty", "empty"), ("movefail", "2 flac file"),
                                         ("exit", "abcde failed")])
def test_incomplete_rips_fail_the_job(abcde, mode, reason):
    run, updates, _ = abcde
    assert run(mode) is False
    assert updates[-1]["status"] == "fail"
    assert reason in updates[-1]["errors"]


def test_shell_expanded_output_path_is_verified(abcde):
    run, updates, conf = abcde
    conf.write_text('OUTPUTTYPE=flac\nOUTPUTDIR="$FAKE_ABCDE_OUT"\n')
    assert run("ok") is True
    assert run("short") is False
    assert "2 flac file" in updates[-1]["errors"]


def test_existing_files_do_not_count_toward_this_rip(abcde, tmp_path):
    run, updates, _ = abcde
    output = tmp_path / "music/Artist/sr0"
    output.mkdir(parents=True)
    (output / "3.flac").write_bytes(b"previous rip")
    assert run("short") is False
    assert "2 flac file" in updates[-1]["errors"]


def test_concurrent_jobs_validate_only_their_own_files(abcde, tmp_path, monkeypatch):
    run, _, _ = abcde
    barrier = tmp_path / "barrier"
    barrier.mkdir()
    monkeypatch.setenv("FAKE_ABCDE_BARRIER", str(barrier))
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run, "ok", device) for device in ("sr0", "sr1")]
        assert [future.result(timeout=10) for future in futures] == [True, True]


@pytest.mark.parametrize("types", ["flac,mp3", "vorbis"])
def test_multiple_formats_and_vorbis_alias(abcde, types):
    run, _, conf = abcde
    conf.write_text('OUTPUTTYPE=%s\nOUTPUTDIR="$FAKE_ABCDE_OUT"\n' % types)
    assert run("ok") is True


def test_custom_container_is_verified_by_output_type(abcde):
    run, _, conf = abcde
    conf.write_text('OUTPUTTYPE=flac\nFLACOUTPUTCONTAINER=oga\nOUTPUTDIR="$FAKE_ABCDE_OUT"\n')
    assert run("ok") is True


def test_relative_output_paths_are_recorded_as_absolute(abcde, tmp_path, monkeypatch):
    run, _, conf = abcde
    monkeypatch.chdir(tmp_path)
    conf.write_text('OUTPUTTYPE=flac\nOUTPUTDIR=relative-music\n')
    assert run("ok") is True


def test_config_path_and_output_names_can_contain_shell_metacharacters(abcde, tmp_path, monkeypatch):
    import arm.config.config as cfg
    run, _, conf = abcde
    custom = tmp_path / "config with 'quotes'.conf"
    conf.rename(custom)
    monkeypatch.setitem(cfg.arm_config, "ABCDE_CONFIG_FILE", str(custom))
    custom.write_text('OUTPUTTYPE=flac\nOUTPUTDIR="$FAKE_ABCDE_OUT/Album with \'quotes\'"\n')
    assert run("ok") is True


def test_manifest_rejects_missing_outputs(tmp_path):
    from arm.ripper.abcde import output_error
    manifest = tmp_path / "outputs"
    manifest.write_bytes(b"flac\0" + os.fsencode(tmp_path / "missing.flac") + b"\0")
    types = tmp_path / "types"
    types.write_text("flac")
    assert "missing or unreadable" in output_error(manifest, types, 1)


def test_empty_manifest_cannot_succeed_when_track_count_is_unavailable(tmp_path):
    from arm.ripper.abcde import output_error
    manifest, types = tmp_path / "outputs", tmp_path / "types"
    manifest.write_bytes(b"")
    types.write_text("flac")
    assert output_error(manifest, types, None) == "abcde produced no flac files"
