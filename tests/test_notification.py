"""Pure-logic tests for FBNS push parsing + live-start detection."""
from ig_live_detector.fbns.notification import (
    LIVE_END_KEYS,
    LIVE_START_KEYS,
    extract_live_broadcast,
    parse_notification,
)


def test_parse_short_keys_and_source():
    n = parse_notification({"t": "Title", "m": "Body", "collapse_key": "live_broadcast", "s": "456"})
    assert n["title"] == "Title"
    assert n["message"] == "Body"
    assert n["collapse_key"] == "live_broadcast"
    assert n["source_user_id"] == "456"


def test_parse_source_none_ignored():
    n = parse_notification({"s": "None"})
    assert "source_user_id" not in n


def test_parse_ig_action_params():
    n = parse_notification({"ig": "instagram://live?id=789&reel_id=12"})
    assert n["ig_action"] == "instagram://live?id=789&reel_id=12"
    assert n["action_params"]["id"] == "789"
    assert n["action_params"]["reel_id"] == "12"


def test_extract_live_start():
    n = parse_notification({"collapse_key": "live_broadcast", "s": "456", "ig": "x://live?id=789"})
    r = extract_live_broadcast(n)
    assert r is not None
    assert r["user_id"] == "456"
    assert r["broadcast_id"] == "789"


def test_extract_revoke_is_not_live():
    n = parse_notification({"collapse_key": "live_broadcast_revoke", "s": "456"})
    assert extract_live_broadcast(n) is None


def test_extract_non_live_ignored():
    n = parse_notification({"collapse_key": "direct_v2_message", "s": "456"})
    assert extract_live_broadcast(n) is None


def test_live_key_sets_disjoint():
    assert LIVE_START_KEYS.isdisjoint(LIVE_END_KEYS)
