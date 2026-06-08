"""Runtime config response shape (transcoder_enabled feature gate)."""

from __future__ import annotations

from pydantic import BaseModel


class RuntimeConfigResponse(BaseModel):
    transcoder_enabled: bool
