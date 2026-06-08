"""Default templates per event + render function with per-channel overrides.

Each event_key gets two default strings: a short title and a longer
body. ``render_title_and_body`` uses ``str.format_map`` over the event's
fields. If a channel provides an override template, that's used
instead (with the same variable set).

Missing variables raise ``TemplateRenderError`` instead of silently
returning a partial render — silent partial renders mask typos in
user-configured templates, and a noisy failure is preferable.
"""
from typing import Optional, Tuple

from arm_contracts import ChannelTemplate


class TemplateRenderError(RuntimeError):
    """Raised when a template references a variable that the event
    doesn't carry. The dispatcher catches this and marks the outbox
    row failed with the error in ``last_error``."""


_DEFAULTS = {
    "job.started": (
        "ARM started: {job_title}",
        "Job {job_id} started ripping {job_title} ({job_disc_type}).",
    ),
    "job.rip_complete": (
        "Rip complete: {job_title}",
        "Job {job_id} rip finished in {rip_duration_seconds}s, "
        "{track_count} tracks.",
    ),
    "job.transcode_complete": (
        "Transcode complete: {job_title}",
        "Job {job_id} transcode finished in "
        "{transcode_duration_seconds}s. Output: {output_path}",
    ),
    "job.failed": (
        "ARM job failed: {job_title}",
        "Job {job_id} failed during {phase}: {error_message}",
    ),
    "job.manual_wait_required": (
        "ARM waiting: {job_title}",
        "Job {job_id} is waiting for manual input ({reason}). "
        "{wait_minutes_remaining} minutes remaining.",
    ),
    "job.duplicate_detected": (
        "Duplicate detected: {job_title}",
        "Job {job_id} duplicates existing job {existing_job_id}.",
    ),
}


def render_title_and_body(
    event,
    channel_template: Optional[ChannelTemplate],
) -> Tuple[str, str]:
    """Render (title, body) for an event with optional channel override.

    :param event: a contracts ``NotificationEvent`` instance.
    :param channel_template: optional per-channel override. If a field
        on the template is None, the default for that field is used.
    :raises TemplateRenderError: if a template references a variable
        the event doesn't carry.
    """
    default_title, default_body = _DEFAULTS[event.event_key]
    title_tmpl = (channel_template.title if channel_template and channel_template.title
                  else default_title)
    body_tmpl = (channel_template.body if channel_template and channel_template.body
                 else default_body)

    variables = event.model_dump(mode="python")
    try:
        title = title_tmpl.format_map(variables)
        body = body_tmpl.format_map(variables)
    except KeyError as e:
        raise TemplateRenderError(
            f"template references unknown variable {e.args[0]!r} "
            f"for event {event.event_key}"
        ) from e
    return title, body
