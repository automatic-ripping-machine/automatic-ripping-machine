"""Response helpers for demo route handlers."""
from __future__ import annotations

import datetime
import json
from typing import Any

import httpx


class _DatetimeEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, (datetime.datetime, datetime.date)):
            return o.isoformat()
        return super().default(o)


def json_response(data: Any, status: int = 200) -> httpx.Response:
    content = json.dumps(data, cls=_DatetimeEncoder)
    return httpx.Response(
        status_code=status,
        content=content.encode(),
        headers={"content-type": "application/json"},
    )
