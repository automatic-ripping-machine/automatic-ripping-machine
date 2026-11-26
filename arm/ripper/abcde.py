"""Validate only the files moved by one abcde invocation."""
from contextlib import contextmanager
import os
from pathlib import Path
import shlex
import tempfile


# abcde invokes run_command("movetrack-N", "mv", source, destination).
# Preserve its status/error handling and record only successful track moves.
MOVE_RECORDER = r'''
_arm_run_command=$(declare -f run_command)
if [[ -z "$_arm_run_command" ]]; then
    echo "ARM could not install the abcde output recorder" >&2
    exit 1
fi
eval "${_arm_run_command/run_command ()/__arm_run_command ()}"
unset _arm_run_command
run_command () {
    local arm_status="$1" arm_command="$2" arm_destination="${@: -1}"
    local arm_type="$TMPOUTPUT"
    if [[ "$arm_destination" != /* ]]; then
        arm_destination="$PWD/$arm_destination"
    fi
    __arm_run_command "$@"
    local arm_result=$?
    if [[ "$arm_status" =~ ^movetrack-[0-9]+$ && "$arm_command" == mv && "$arm_result" == 0 ]]; then
        printf '%s\0%s\0' "$arm_type" "$arm_destination" >> "$ARM_OUTPUT_MANIFEST" || return 1
    fi
    return "$arm_result"
}
printf '%s' "$OUTPUTTYPE" > "$ARM_OUTPUT_TYPES" || exit 1
'''


@contextmanager
def output_manifest(config_file):
    """Add recording to abcde's normal configuration without changing its output paths."""
    with tempfile.TemporaryDirectory(prefix="arm-abcde-") as directory:
        root = Path(directory)
        manifest = root / "outputs"
        manifest.touch()
        types = root / "types"
        config = root / "abcde.conf"
        source = f". {shlex.quote(str(config_file))}\n" if os.path.isfile(config_file) else ""
        config.write_text(source + f"ARM_OUTPUT_MANIFEST={shlex.quote(str(manifest))}\n"
                          f"ARM_OUTPUT_TYPES={shlex.quote(str(types))}\n" + MOVE_RECORDER)
        yield config, manifest, types


def output_error(manifest, types, expected):
    """Require one distinct, non-empty moved file per track and configured output type."""
    if not types.is_file():
        return "abcde did not record its output settings; output verification is incomplete"
    formats = {value.strip().split(":")[0] for value in types.read_text().split(",") if value.strip()}
    if not formats:
        return "abcde did not record any output types"
    fields = manifest.read_bytes().split(b"\0")
    if fields[-1] or len(fields) % 2 != 1:
        return "abcde output manifest is incomplete"
    records = {(os.fsdecode(fields[i]), os.fsdecode(fields[i + 1])) for i in range(0, len(fields) - 1, 2)}
    for output_type in sorted(formats):
        files = [path for kind, path in records if kind == output_type]
        if not files:
            return f"abcde produced no {output_type} files"
        if expected is not None and len(files) != expected:
            return f"abcde produced {len(files)} {output_type} file(s); the disc has {expected} audio tracks"
        for path in files:
            try:
                if os.path.getsize(path) <= 0:
                    return f"abcde produced an empty {output_type} file"
            except OSError:
                return f"abcde output file is missing or unreadable: {path}"
    return None
