"""Webhook output: POST to a URL when a live is detected (stdlib only, no extra deps)."""
from __future__ import annotations

import asyncio
import json
import urllib.request
from typing import Optional

from .i18n import t as _t


def _post(url: str, token: Optional[str], payload: dict, timeout: int = 10) -> int:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("X-IGLD-Token", token)
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return getattr(resp, "status", 0) or resp.getcode()


def make_webhook_notifier(url: str, token: Optional[str] = None):
    """Return an async poster: `await notify(payload)` POSTs the payload dict as JSON to the URL."""

    async def notify(payload: dict) -> None:
        loop = asyncio.get_event_loop()
        bid = str(payload.get("broadcast_id", ""))
        try:
            status = await loop.run_in_executor(None, lambda: _post(url, token, payload))
            print(_t("webhook.sent", bid=bid, status=status))
        except Exception as exc:  # noqa: BLE001
            print(_t("webhook.failed", bid=bid, err=exc))

    return notify
