"""Live recording: fetch the playback URL via the instagrapi session, record to mp4 with ffmpeg."""
from __future__ import annotations

import asyncio
import re
import shutil
import subprocess
import time
from pathlib import Path

from .i18n import t as _t

DEFAULT_FILENAME = "ig_live_{username}_{datetime}_part{part:02d}"


def resolve_ffmpeg(ffmpeg: str = "ffmpeg") -> str:
    """Pick the ffmpeg binary: explicit path > system PATH > the one bundled by imageio-ffmpeg."""
    if ffmpeg and ffmpeg != "ffmpeg":
        return ffmpeg  # explicitly specified
    if shutil.which(ffmpeg or "ffmpeg"):
        return ffmpeg or "ffmpeg"  # found on the system
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()  # bundled copy
    except Exception:
        return ffmpeg or "ffmpeg"


def fetch_playback_url(cl, broadcast_id: str) -> tuple[str, str]:
    """Return (broadcast_status, dash_url); ('', '') when unavailable."""
    data = cl.private_request(f"live/{broadcast_id}/info/")
    status = str(data.get("broadcast_status") or "")
    url = data.get("dash_abr_playback_url") or data.get("dash_playback_url") or ""
    return status, url


def resolve_broadcast_id(cl, user_id: str) -> str:
    """Fetch the user's story via instagrapi and read broadcast_id from the broadcast object; '' if none."""
    data = cl.private_request(f"feed/user/{user_id}/story/")
    bc = data.get("broadcast") if isinstance(data, dict) else None
    if bc:
        return str(bc.get("id") or bc.get("pk") or "")
    return ""


def resolve_username(cl, user_id: str) -> str:
    """Resolve username from user_id (for readable filenames); fall back to the user_id string."""
    fn = getattr(cl, "username_from_user_id", None)
    if fn:
        try:
            return str(fn(user_id)) or str(user_id)
        except Exception:
            pass
    try:
        return str(cl.user_info(user_id).username) or str(user_id)
    except Exception:
        return str(user_id)


def _safe_component(s: str) -> str:
    """Sanitize a single path segment (illegal chars -> _)."""
    return re.sub(r"[^\w.\-]", "_", s)[:200] or "ig_live"


def _build_relpath(template: str, **fields) -> Path:
    """Render the template into a relative path; '/' means a subfolder; sanitize and block . / .. traversal."""
    try:
        raw = template.format(**fields)
    except Exception:
        raw = DEFAULT_FILENAME.format(**fields)
    parts = []
    for comp in raw.replace("\\", "/").split("/"):
        comp = comp.strip()
        if comp in ("", ".", ".."):
            continue
        parts.append(_safe_component(comp))
    return Path(*parts) if parts else Path("ig_live")


def record(
    broadcast_id: str,
    dash_url: str,
    output_dir: str,
    username: str = "",
    ffmpeg: str = "ffmpeg",
) -> subprocess.Popen:
    """Start ffmpeg to record the dash stream into an mp4 (copy, faststart)."""
    ts = time.strftime("%Y%m%d_%H%M%S")
    name = (username or broadcast_id).lstrip("@") or broadcast_id
    out_dir = Path(output_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"ig_live_{name}_{ts}.mp4"
    return subprocess.Popen(_ffmpeg_cmd(resolve_ffmpeg(ffmpeg), dash_url, out_path))


def _ffmpeg_cmd(ffmpeg: str, dash_url: str, out_path: Path) -> list[str]:
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "warning",
        "-rw_timeout",
        "30000000",  # 30s I/O 逾時：來源卡住時讓 ffmpeg 結束以觸發續錄
        "-i",
        dash_url,
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        "-y",
        str(out_path),
    ]


async def supervise_recording(
    cl,
    broadcast_id: str,
    user_id: str,
    output_dir: str,
    ffmpeg: str = "ffmpeg",
    *,
    filename_template: str = DEFAULT_FILENAME,
    min_healthy_sec: int = 15,
    max_fast_fails: int = 5,
    max_restarts: int = 200,
    base_backoff: int = 3,
    max_backoff: int = 30,
    max_initial_retries: int = 3,
    initial_backoff: int = 3,
) -> None:
    """Record one live, resuming on interruption until the broadcast ends. Multiple anti-loop guards.

    Interruption (ffmpeg dies while the live is still active) -> re-fetch URL, record the next part.
    Filename uses filename_template (fields: {username}/{user_id}/{broadcast_id}/{datetime}/{part}).
    max_fast_fails consecutive fast failures (under min_healthy_sec) -> give up; max_restarts is a hard cap.
    """
    out_dir = Path(output_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = resolve_ffmpeg(ffmpeg)
    datetime_str = time.strftime("%Y%m%d_%H%M%S")
    loop = asyncio.get_event_loop()
    try:
        username = await loop.run_in_executor(None, lambda: resolve_username(cl, user_id))
    except Exception:
        username = str(user_id)
    username = (username or str(user_id)).lstrip("@")

    part = 0
    restarts = 0
    fast_fails = 0
    initial_retries = 0
    backoff = base_backoff

    while True:
        fetch_error = False
        try:
            status, url = await loop.run_in_executor(
                None, lambda: fetch_playback_url(cl, broadcast_id)
            )
        except Exception as exc:  # noqa: BLE001
            print(_t("rec.info_failed", bid=broadcast_id, err=exc))
            status, url = "", ""
            fetch_error = True

        if status != "active" or not url:
            # 初次拓不到且屬暫時性錯誤時短重試，避免因網路抖動放棄整場
            if part == 0 and fetch_error and initial_retries < max_initial_retries:
                initial_retries += 1
                await asyncio.sleep(initial_backoff)
                continue
            if part == 0:
                print(_t("rec.not_active", bid=broadcast_id))
            else:
                print(_t("rec.ended", bid=broadcast_id, parts=part))
            return

        part += 1
        rel = _build_relpath(
            filename_template,
            username=username,
            user_id=user_id,
            broadcast_id=broadcast_id,
            datetime=datetime_str,
            part=part,
        )
        out_path = out_dir / f"{rel}.mp4"
        out_path.parent.mkdir(parents=True, exist_ok=True)  # create subfolders when the template has them
        print(_t("rec.recording", bid=broadcast_id, part=part, path=out_path))
        started = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(*_ffmpeg_cmd(ffmpeg, url, out_path))
            await proc.wait()
        except FileNotFoundError:
            print(_t("rec.ffmpeg_missing", ffmpeg=ffmpeg))
            return
        except asyncio.CancelledError:
            if "proc" in locals():
                try:
                    proc.terminate()
                except Exception:
                    pass
            raise
        except Exception as exc:  # noqa: BLE001
            print(_t("rec.ffmpeg_failed", bid=broadcast_id, err=exc))
        ran = time.monotonic() - started

        restarts += 1
        if restarts >= max_restarts:
            print(_t("rec.max_restarts", bid=broadcast_id, limit=max_restarts))
            return

        if ran < min_healthy_sec:
            fast_fails += 1
            if fast_fails >= max_fast_fails:
                print(_t("rec.fast_fails", bid=broadcast_id, count=fast_fails))
                return
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)
        else:
            fast_fails = 0
            backoff = base_backoff
            await asyncio.sleep(1)  # brief pause to avoid any tight loop
