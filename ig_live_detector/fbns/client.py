"""FBNS client: connect to FBNS with an instagrapi session and receive live push notifications.

Flow: inject session and connect -> CONNACK yields device-auth -> subscribe 76 -> send 79 reg_req
-> receive 80 for the token -> callback does push/register (externally, with instagrapi) -> listen on 76.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Awaitable, Callable, Optional

from ..i18n import t as _t
from .connection import FbnsConnectConfig, build_fbns_connect_thrift
from .mqttot import MQTToTClient
from .notification import parse_notification

FBNS_HOST = "mqtt-mini.facebook.com"
FBNS_PORT = 443
INSTAGRAM_PACKAGE_NAME = "com.instagram.android"
FB_ANALYTICS_APP_ID = 567067343352427  # used by reg_req
CONNECT_APP_ID = 567310203415052  # used by the connect thrift

TOPIC_FBNS_MESSAGE = "76"
TOPIC_FBNS_REG_REQ = "79"
TOPIC_FBNS_REG_RESP = "80"


def build_fbns_user_agent(device_settings: dict, language: str = "en_US") -> str:
    ds = device_settings or {}
    res = str(ds.get("resolution", "1080x1920"))
    width, _, height = res.partition("x")
    params = [
        ("FBAN", "MQTT"),
        ("FBAV", str(ds.get("app_version", ""))),
        ("FBBV", str(ds.get("version_code", ""))),
        ("FBDM", f"{{density=4.0,width={width},height={height}"),
        ("FBLC", language),
        ("FBCR", "Android"),
        ("FBMF", str(ds.get("manufacturer", "")).strip()),
        ("FBBD", "Android"),
        ("FBPN", INSTAGRAM_PACKAGE_NAME),
        ("FBDV", str(ds.get("model", "")).strip()),
        ("FBSV", str(ds.get("android_release", ""))),
        ("FBLR", "0"),
        ("FBBK", "1"),
        ("FBCA", "x86:armeabi-v7a"),
    ]
    return "[" + ";".join(f"{k}/{v}" for k, v in params) + "]"


class FbnsClient:
    def __init__(
        self,
        settings: dict,
        on_push: Callable[[dict], Awaitable[None]],
        register_token: Callable[[str], Awaitable[None]],
    ) -> None:
        self.settings = settings
        self.on_push = on_push
        self.register_token = register_token
        self._client = MQTToTClient()
        self._token_future: Optional[asyncio.Future] = None

    def _build_config(self) -> FbnsConnectConfig:
        # Always use a fresh connection (empty device-auth): reusing the server-issued device-auth gets dropped instantly
        s = self.settings
        uuids = s.get("uuids", {})
        device_settings = s.get("device_settings", {})
        phone_id = uuids.get("phone_id", "")
        return FbnsConnectConfig(
            client_identifier=phone_id[:20],
            user_agent=build_fbns_user_agent(device_settings, s.get("locale", "en_US")),
            client_mqtt_session_id=int(time.time() * 1000) & 0xFFFFFFFF,
            app_id=CONNECT_APP_ID,
        )

    async def start(self) -> asyncio.Task:
        """Connect and finish registration; return the background listen task (keeps receiving push)."""
        self._client.on_message = self._on_message
        payload = build_fbns_connect_thrift(self._build_config())
        await self._client.connect(FBNS_HOST, FBNS_PORT, 60, payload)

        self._token_future = asyncio.get_event_loop().create_future()
        listen_task = asyncio.create_task(self._client.listen())
        try:
            await self._client.subscribe(TOPIC_FBNS_MESSAGE)
            reg_req = json.dumps(
                {"pkg_name": INSTAGRAM_PACKAGE_NAME, "appid": FB_ANALYTICS_APP_ID}
            ).encode("utf-8")
            await self._client.publish(TOPIC_FBNS_REG_REQ, reg_req, qos=1)
            token = await asyncio.wait_for(self._token_future, timeout=30)
            await self.register_token(token)
        except BaseException:
            listen_task.cancel()
            raise
        return listen_task

    async def run_forever(self, on_ready: Optional[Callable[[], None]] = None) -> None:
        """Run forever: auto-reconnect on disconnect (including after first registration); each reconnect is fresh."""
        backoff = 2
        while True:
            try:
                listen_task = await self.start()
                if on_ready:
                    on_ready()
                backoff = 2
                await listen_task
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                msg = str(exc).lower()
                if any(k in msg for k in ("login_required", "challenge_required", "401", "not logged", "checkpoint")):
                    print(_t("fbns.session_expired"))
                else:
                    print(_t("fbns.disconnected", kind=type(exc).__name__, err=exc, backoff=backoff))
            try:
                await self._client.disconnect()
            except Exception:
                pass
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 15)

    async def _on_message(self, topic: str, payload: bytes) -> None:
        if topic == TOPIC_FBNS_REG_RESP:
            data = _loads(payload)
            token = data.get("token")
            if token and self._token_future and not self._token_future.done():
                self._token_future.set_result(token)
        elif topic == TOPIC_FBNS_MESSAGE:
            data = _loads(payload)
            notif = data.get("fbpushnotif")
            if notif:
                await self.on_push(parse_notification(notif))

    async def disconnect(self) -> None:
        await self._client.disconnect()


def _loads(payload: bytes) -> dict:
    try:
        obj = json.loads(payload.decode("utf-8", "replace"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}
