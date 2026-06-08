"""Settings response shape."""

from __future__ import annotations

from pydantic import BaseModel

from backend.models.transcoder import TranscoderAuthStatus, TranscoderConfig


class SettingsResponse(BaseModel):
    arm_config: dict[str, str | None] | None = None
    arm_metadata: dict[str, str] | None = None
    naming_variables: dict[str, str] | None = None
    transcoder_config: TranscoderConfig | None = None
    transcoder_gpu_support: dict[str, bool] | None = None
    transcoder_auth_status: TranscoderAuthStatus | None = None
    # Whether arm-ui has its own outbound webhook secret configured (loaded
    # from ARM_UI_TRANSCODER_WEBHOOK_SECRET at startup; rotation needs a
    # restart per feedback_arm_ui_webhook_secret_load_once). Operators need
    # both this and transcoder_auth_status.webhook_secret_configured to be
    # true for outbound webhooks to authenticate.
    arm_ui_webhook_secret_configured: bool = False
    # Deprecated; mirrors transcoder_gpu_support
    gpu_support: dict[str, bool] | None = None
