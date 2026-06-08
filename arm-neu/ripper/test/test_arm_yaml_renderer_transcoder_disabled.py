"""Renderer test: when ARM_TRANSCODER_ENABLED=false, TRANSCODER_URL must be empty.

The arm.yaml renderer lives in scripts/docker/runit/arm_user_files_setup.sh and
uses sed to patch a freshly-copied arm.yaml. This test extracts just the
relevant block into a standalone shell snippet and runs it against a fixture
yaml to verify the behavior without booting a container.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap


# Literal docker-compose endpoint used only as test fixture data; no network
# call is made. The renderer under test treats this as an opaque string.
_TEST_WEBHOOK = "http://arm-transcoder:5000/webhook/arm"  # NOSONAR
_IGNORED_WEBHOOK = "http://should-be-ignored:5000/webhook/arm"  # NOSONAR

FIXTURE_YAML = textwrap.dedent(
    f"""\
    SKIP_TRANSCODE: false
    TRANSCODER_URL: "{_TEST_WEBHOOK}"
    TRANSCODER_WEBHOOK_SECRET: "some-secret"
    LOCAL_RAW_PATH: ""
    SHARED_RAW_PATH: ""
    """
)


RENDER_SNIPPET = textwrap.dedent(
    """\
    ARM_YAML="$1"
    apply_yaml_override() {
      local key="$1" envvar="$2"
      if [[ -n "${!envvar:-}" ]] && grep -q "^${key}:" "$ARM_YAML"; then
        sed -i "s|^${key}:.*|${key}: \\"${!envvar}\\"|" "$ARM_YAML"
      fi
      return 0
    }
    force_yaml_empty() {
      local key="$1"
      if grep -q "^${key}:" "$ARM_YAML"; then
        sed -i "s|^${key}:.*|${key}: \\"\\"|" "$ARM_YAML"
      fi
    }
    if [[ "${ARM_TRANSCODER_ENABLED:-true}" == "false" ]]; then
      force_yaml_empty TRANSCODER_URL
      force_yaml_empty TRANSCODER_WEBHOOK_SECRET
    else
      apply_yaml_override TRANSCODER_URL ARM_TRANSCODER_URL
      apply_yaml_override TRANSCODER_WEBHOOK_SECRET ARM_TRANSCODER_WEBHOOK_SECRET
    fi
    """
)


def _render(env: dict[str, str]) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write(FIXTURE_YAML)
        path = f.name
    try:
        merged_env = dict(os.environ)
        merged_env.update(env)
        subprocess.run(
            ["bash", "-c", RENDER_SNIPPET, "bash", path],
            check=True,
            env=merged_env,
        )
        with open(path) as f:
            return f.read()
    finally:
        os.unlink(path)


def _get_value(rendered: str, key: str) -> str:
    for line in rendered.splitlines():
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip().strip('"')
    raise KeyError(key)


def test_transcoder_url_empty_when_disabled():
    rendered = _render({
        "ARM_TRANSCODER_ENABLED": "false",
        "ARM_TRANSCODER_URL": _IGNORED_WEBHOOK,
        "ARM_TRANSCODER_WEBHOOK_SECRET": "should-be-wiped",
    })
    assert _get_value(rendered, "TRANSCODER_URL") == ""
    assert _get_value(rendered, "TRANSCODER_WEBHOOK_SECRET") == ""


def test_transcoder_url_preserved_when_enabled():
    rendered = _render({
        "ARM_TRANSCODER_ENABLED": "true",
        "ARM_TRANSCODER_URL": _TEST_WEBHOOK,
        "ARM_TRANSCODER_WEBHOOK_SECRET": "secret",
    })
    assert _get_value(rendered, "TRANSCODER_URL") == _TEST_WEBHOOK
    assert _get_value(rendered, "TRANSCODER_WEBHOOK_SECRET") == "secret"


def test_transcoder_url_preserved_when_flag_unset():
    rendered = _render({
        "ARM_TRANSCODER_URL": _TEST_WEBHOOK,
        "ARM_TRANSCODER_WEBHOOK_SECRET": "secret",
    })
    assert _get_value(rendered, "TRANSCODER_URL") == _TEST_WEBHOOK
    assert _get_value(rendered, "TRANSCODER_WEBHOOK_SECRET") == "secret"
