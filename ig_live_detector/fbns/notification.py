"""Parse FBNS fbpushnotif (mirrors MIT instagram_mqtt's createNotificationFromJson)."""
from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

# fbpushnotif short keys -> semantic field names
_KEYS = {
    "t": "title",
    "m": "message",
    "tt": "ticker_text",
    "collapse_key": "collapse_key",
    "i": "optional_image",
    "a": "optional_avatar_url",
    "sound": "sound",
    "pi": "push_id",
    "c": "push_category",
    "u": "intended_recipient_user_id",
    "igo": "ig_action_override",
    "ia": "in_app_actors",
}


def parse_notification(fbpushnotif) -> dict:
    data = fbpushnotif if isinstance(fbpushnotif, dict) else json.loads(fbpushnotif)
    n: dict = {"raw": data}
    for short, name in _KEYS.items():
        if data.get(short) is not None:
            n[name] = data[short]
    # s = source user (the broadcaster); 'None' means absent
    if data.get("s") and data["s"] != "None":
        n["source_user_id"] = data["s"]
    # ig = action URL (instagram://...?query) -> split path and params
    if data.get("ig"):
        n["ig_action"] = data["ig"]
        url = urlparse(data["ig"])
        if url.path:
            n["action_path"] = url.path
        if url.query:
            n["action_params"] = {
                k: (v[0] if len(v) == 1 else v) for k, v in parse_qs(url.query).items()
            }
    return n


# collapse_key values that mean "live started" (known constants from instagram_mqtt)
LIVE_START_KEYS = {"live_broadcast", "live_with_broadcast"}
# live ended / revoked (must NOT be treated as a start)
LIVE_END_KEYS = {"live_broadcast_revoke"}


def extract_live_broadcast(notif: dict) -> dict | None:
    """If it's a "live started" notification, return {'broadcast_id'?, 'user_id', ...}; otherwise None.

    Detection uses known collapse_key values (live_broadcast / live_with_broadcast), excluding end events.
    broadcast_id isn't always in the push; when present it's in action_params, otherwise the caller
    resolves it from user_id via instagrapi. user_id comes from source_user_id (the push `s` field).
    """
    ck = str(notif.get("collapse_key") or "")
    if ck not in LIVE_START_KEYS:
        return None
    params = notif.get("action_params") or {}
    bid = (
        params.get("broadcast_id")
        or params.get("id")
        or params.get("reel_id")
        or params.get("media_id")
    )
    return {
        "broadcast_id": bid,
        "user_id": notif.get("source_user_id"),
        "collapse_key": ck,
        "action_path": notif.get("action_path"),
        "action_params": params,
    }
