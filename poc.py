"""Pure-Python FBNS PoC: connect to FBNS and receive live push (push/register via instagrapi).

Usage:
    IG_SETTINGS_FILE=/path/to/instagrapi_settings.json python3 poc.py
"""
import asyncio
import json
import os
import sys
import uuid as _uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ig_live_detector.fbns.client import FbnsClient
from ig_live_detector.fbns.notification import extract_live_broadcast

SETTINGS_FILE = os.environ.get("IG_SETTINGS_FILE", "").strip()


def load_settings() -> dict:
    if not SETTINGS_FILE or not Path(SETTINGS_FILE).exists():
        print("Set IG_SETTINGS_FILE to point at instagrapi_settings.json")
        sys.exit(1)
    return json.loads(Path(SETTINGS_FILE).read_text(encoding="utf-8"))


def make_register(settings: dict):
    """Return async register(token): call push/register with the instagrapi signature."""
    from instagrapi import Client

    cl = Client()
    cl.set_settings(settings)
    uuids = settings.get("uuids", {})
    cookies = settings.get("cookies", {})

    async def register(token: str) -> None:
        data = {
            "device_type": "android_mqtt",
            "is_main_push_channel": "true",
            "device_sub_type": "2",
            "device_token": token,
            "_csrftoken": cookies.get("csrftoken", ""),
            "guid": uuids.get("uuid", ""),
            "uuid": uuids.get("uuid", ""),
            "users": cookies.get("ds_user_id", ""),
            "family_device_id": str(_uuid.uuid4()),
        }
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(
            None,
            lambda: cl.private_request("push/register/", data=data, with_signature=False),
        )
        print("✅ push/register response:", str(res)[:200])

    return register


async def on_push(notif: dict) -> None:
    ck = notif.get("collapse_key")
    print(f"\n🔔 PUSH collapse_key={ck}")
    print(json.dumps(notif, ensure_ascii=False)[:800])
    live = extract_live_broadcast(notif)
    if live:
        print(f"🔴 Live detected! broadcast_id={live.get('broadcast_id')} user_id={live.get('user_id')}")


def main() -> None:
    settings = load_settings()

    client = FbnsClient(
        settings=settings,
        on_push=on_push,
        register_token=make_register(settings),
    )

    async def run() -> None:
        print("Connecting to FBNS...")
        await client.run_forever(
            on_ready=lambda: print("🟢 Connected and registered, waiting for live push (Ctrl+C to stop)")
        )

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
