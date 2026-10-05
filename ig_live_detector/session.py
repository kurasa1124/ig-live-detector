"""instagrapi session storage and login."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


def load_settings(path: str) -> Optional[dict]:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_settings(path: str, settings: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(settings), encoding="utf-8")


def build_client(settings: dict):
    """Build an instagrapi Client from an existing session (no re-login)."""
    from instagrapi import Client

    cl = Client()
    cl.set_settings(settings)
    return cl


def login(username: str, password: str, settings_path: str, verification_code: str = ""):
    """Log in with username/password (+ optional 2FA/backup code), keep the same device, save the session."""
    from instagrapi import Client

    cl = Client()
    existing = load_settings(settings_path)
    if existing:
        try:
            cl.set_settings(existing)  # keep the same device
        except Exception:
            pass
    if verification_code:
        cl.login(username, password, verification_code=verification_code)
    else:
        cl.login(username, password)
    save_settings(settings_path, cl.get_settings())
    return cl
