"""High-level API for using ig-live-detector as a library from other projects.

Typical usage (from another project)::

    import asyncio, json
    from ig_live_detector import watch_lives

    settings = json.load(open("session.json"))  # instagrapi get_settings()

    async def on_live(broadcast_id, user_id, notif):
        ...  # caller's choice: record, call a webhook, notify...

    asyncio.run(watch_lives(settings, on_live))
"""
from __future__ import annotations

import asyncio
import uuid as _uuid
from typing import Awaitable, Callable, Optional

from .fbns.client import FbnsClient
from .fbns.notification import extract_live_broadcast
from .i18n import t as _t
from .session import build_client

# on_live(broadcast_id, user_id, notif)
OnLive = Callable[[str, str, dict], Awaitable[None]]


def resolve_target_uids(cl, targets: list[str]) -> set[str]:
    """Resolve targets (username or uid) into a set of uid strings; pure digits are used as-is."""
    uids: set[str] = set()
    for target in targets:
        target = target.strip().lstrip("@")
        if not target:
            continue
        if target.isdigit():
            uids.add(target)
            continue
        try:
            uids.add(str(cl.user_id_from_username(target)))
        except Exception as exc:  # noqa: BLE001
            print(_t("target.resolve_failed", name=target, err=exc))
    return uids


def make_register_token(cl, settings: dict):
    """Return the register_token callback FbnsClient needs (calls push/register with instagrapi)."""
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
        await loop.run_in_executor(
            None, lambda: cl.private_request("push/register/", data=data, with_signature=False)
        )

    return register


async def watch_lives(
    settings: dict,
    on_live: OnLive,
    *,
    client=None,
    targets: Optional[list[str]] = None,
    on_ready: Optional[Callable[[], None]] = None,
) -> None:
    """Run forever: connect to FBNS and call on_live(broadcast_id, user_id, notif) on a live push.

    settings: an instagrapi get_settings() dict (must hold a valid login session).
    client: pass a custom instagrapi Client; otherwise one is built from settings.
    targets: only record these accounts (username or uid); empty = record every followed account.
    """
    cl = client or build_client(settings)
    register = make_register_token(cl, settings)

    target_uids: set[str] = set()
    if targets:
        loop = asyncio.get_event_loop()
        target_uids = await loop.run_in_executor(None, lambda: resolve_target_uids(cl, targets))
        print(_t("target.only", uids=target_uids or _t("target.all_failed")))

    async def on_push(notif: dict) -> None:
        live = extract_live_broadcast(notif)
        if not live:
            return
        uid = str(live.get("user_id") or "")
        if target_uids and uid not in target_uids:
            return  # not in the list, skip
        bid = str(live.get("broadcast_id") or "")
        if not bid and uid:
            # push lacks broadcast_id -> fetch via the user's story
            from . import recorder

            loop = asyncio.get_event_loop()
            try:
                bid = await loop.run_in_executor(
                    None, lambda: recorder.resolve_broadcast_id(cl, uid)
                )
            except Exception as exc:  # noqa: BLE001
                print(_t("bid.resolve_failed", uid=uid, err=exc))
                return
        if not bid:
            print(_t("bid.missing", uid=uid, notif=notif))
            return
        try:
            await on_live(bid, uid, notif)
        except Exception as exc:  # noqa: BLE001
            # consumer 的 callback 出錯只記錄，不影響 FBNS 連線
            print(_t("onlive.error", uid=uid, err=exc))

    fbns = FbnsClient(settings=settings, on_push=on_push, register_token=register)
    await fbns.run_forever(on_ready=on_ready)


async def run_detector(
    settings: dict,
    *,
    record: bool = True,
    webhook: Optional[str] = None,
    webhook_token: Optional[str] = None,
    output_dir: str = "recordings",
    ffmpeg: str = "ffmpeg",
    filename_template: str = "ig_live_{username}_{datetime}_part{part:02d}",
    client=None,
    targets: Optional[list[str]] = None,
    on_ready: Optional[Callable[[], None]] = None,
) -> None:
    """Detection core. On each detected live, run the configured outputs (any combination):

    - webhook: POST {broadcast_id, user_id, username} to `webhook` (optional token header).
    - record: fetch the playback URL and record to mp4 (with resume).

    Both outputs are optional and composable. Runs forever.
    """
    from . import recorder
    from .webhook import make_webhook_notifier

    cl = client or build_client(settings)
    active: dict[str, asyncio.Task] = {}
    notifier = make_webhook_notifier(webhook, webhook_token) if webhook else None

    async def on_live(broadcast_id: str, user_id: str, notif: dict) -> None:
        if notifier is not None:
            loop = asyncio.get_event_loop()
            username = ""
            try:
                username = await loop.run_in_executor(
                    None, lambda: str(recorder.resolve_username(cl, user_id))
                )
            except Exception:  # noqa: BLE001
                username = ""
            # igld 有 session，順手取 playback URL 一起送，收端不必再登入 IG
            status, playback_url = "", ""
            try:
                status, playback_url = await loop.run_in_executor(
                    None, lambda: recorder.fetch_playback_url(cl, broadcast_id)
                )
            except Exception as exc:  # noqa: BLE001
                print(_t("webhook.url_failed", bid=broadcast_id, err=exc))
            await notifier(
                {
                    "broadcast_id": broadcast_id,
                    "user_id": user_id,
                    "username": username,
                    "status": status,
                    "playback_url": playback_url,
                }
            )

        if record:
            task = active.get(broadcast_id)
            if task is not None and not task.done():
                return  # already recording this one
            new_task = asyncio.create_task(
                recorder.supervise_recording(
                    cl,
                    broadcast_id,
                    user_id,
                    output_dir,
                    ffmpeg,
                    filename_template=filename_template,
                )
            )
            active[broadcast_id] = new_task

            def _done(t: asyncio.Task, bid: str = broadcast_id) -> None:
                active.pop(bid, None)
                if not t.cancelled() and t.exception() is not None:
                    print(_t("rec.task_error", bid=bid, err=t.exception()))

            new_task.add_done_callback(_done)

    await watch_lives(settings, on_live, client=cl, targets=targets, on_ready=on_ready)


async def record_lives(
    settings: dict,
    *,
    output_dir: str = "recordings",
    ffmpeg: str = "ffmpeg",
    filename_template: str = "ig_live_{username}_{datetime}_part{part:02d}",
    client=None,
    targets: Optional[list[str]] = None,
    on_ready: Optional[Callable[[], None]] = None,
) -> None:
    """Detect lives and record them to mp4 (with resume). Thin wrapper over run_detector(record=True)."""
    await run_detector(
        settings,
        record=True,
        output_dir=output_dir,
        ffmpeg=ffmpeg,
        filename_template=filename_template,
        client=client,
        targets=targets,
        on_ready=on_ready,
    )
