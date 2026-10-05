"""Lightweight i18n for user-facing messages (English primary, Chinese secondary).

Language is resolved once from the ``IGLD_LANG`` environment variable
(``en`` / ``zh``), falling back to the system locale, then to English.
"""
from __future__ import annotations

import locale
import os
from typing import Optional

_lang: Optional[str] = None


def _detect() -> str:
    env = (os.environ.get("IGLD_LANG") or "").strip().lower()
    if env:
        return "zh" if env.startswith("zh") else "en"
    try:
        loc = locale.getlocale()[0] or ""
    except Exception:
        loc = ""
    return "zh" if loc.lower().startswith("zh") else "en"


def lang() -> str:
    global _lang
    if _lang is None:
        _lang = _detect()
    return _lang


def set_lang(value: str) -> None:
    """Override the language explicitly (``en`` or ``zh``)."""
    global _lang
    _lang = "zh" if value.lower().startswith("zh") else "en"


# key -> {"en": ..., "zh": ...}; use {name} placeholders filled via t(key, name=...)
MESSAGES: dict[str, dict[str, str]] = {
    # CLI: argparse
    "cli.desc": {
        "en": "Pure-Python Instagram Live detector via FBNS push + auto recorder.",
        "zh": "純 Python：用 IG FBNS 推播偵測開直播，自動錄影。",
    },
    "cli.login.help": {
        "en": "Log in to Instagram and save the session (interactive).",
        "zh": "登入 IG 並存 session（互動式）。",
    },
    "cli.login.username.help": {
        "en": "Instagram username (asked interactively if omitted).",
        "zh": "IG 帳號（省略會互動詢問）。",
    },
    "cli.login.code.help": {
        "en": "2FA code or backup code (asked when needed if omitted).",
        "zh": "2FA 驗證碼或備用碼（省略會在需要時詢問）。",
    },
    "cli.run.help": {
        "en": "Connect to FBNS, detect lives and auto-record.",
        "zh": "連 FBNS 偵測直播並自動錄影。",
    },
    # CLI: login flow
    "login.need_settings": {
        "en": "Set the IGLD_SETTINGS env var to the session file path first.",
        "zh": "請先設環境變數 IGLD_SETTINGS 指向要存的 session 檔路徑。",
    },
    "run.need_settings": {
        "en": "Set the IGLD_SETTINGS env var and run `igld login` first.",
        "zh": "請先設環境變數 IGLD_SETTINGS，並先執行 igld login。",
    },
    "run.stopped": {"en": "Stopped.", "zh": "結束。"},
    "login.prompt_username": {"en": "Instagram username: ", "zh": "IG 帳號："},
    "login.no_username": {"en": "No username entered.", "zh": "未輸入帳號。"},
    "login.prompt_password": {"en": "Instagram password (hidden): ", "zh": "IG 密碼（不會顯示）："},
    "login.prompt_2fa": {
        "en": "This account needs 2FA. Enter the verification or backup code: ",
        "zh": "此帳號需要兩步驗證，請輸入驗證碼或備用碼：",
    },
    "login.no_code": {"en": "No code entered.", "zh": "未輸入驗證碼。"},
    "login.failed": {
        "en": "✗ Login failed: {kind}: {msg}",
        "zh": "✗ 登入失敗：{kind}: {msg}",
    },
    "login.needs_upgrade": {
        "en": "✗ This account is blocked by IG's version check (needs_upgrade) — common for "
        "very new or flagged accounts. Try a different account.",
        "zh": "✗ 這個帳號被 IG 擋在版本檢查外（needs_upgrade）——多見於太新/被標記的帳號，請換一個帳號再試。",
    },
    "login.success": {
        "en": "✅ Logged in. Session saved to: {path}",
        "zh": "✅ 登入成功，session 已存：{path}",
    },
    # app
    "app.no_session": {
        "en": "Session not found: {path}. Run `igld login` first.",
        "zh": "找不到 session：{path}，請先執行 igld login。",
    },
    "app.ready": {
        "en": "🟢 Connected to FBNS, waiting for live push notifications.",
        "zh": "🟢 已連線 FBNS，等待開直播推播。",
    },
    # targets
    "target.resolve_failed": {
        "en": "⚠️ Failed to resolve target {name}: {err}",
        "zh": "⚠️ 解析目標 {name} 失敗：{err}",
    },
    "target.only": {
        "en": "Watching only target uids: {uids}",
        "zh": "只監聽目標 uid：{uids}",
    },
    "target.all_failed": {
        "en": "(all failed to resolve, watching everyone)",
        "zh": "(全部解析失敗，改監聽全部)",
    },
    # broadcast id
    "bid.resolve_failed": {
        "en": "✗ Failed to resolve broadcast_id for user={uid}: {err}",
        "zh": "✗ 以 user={uid} 解析 broadcast_id 失敗：{err}",
    },
    "bid.missing": {
        "en": "⚠️ Got a live push but no broadcast_id (user={uid}): {notif}",
        "zh": "⚠️ 收到開直播通知但拿不到 broadcast_id（user={uid}）：{notif}",
    },
    "onlive.error": {
        "en": "✗ on_live callback error (user={uid}): {err}",
        "zh": "✗ on_live callback 發生錯誤（user={uid}）：{err}",
    },
    # recorder
    "rec.info_failed": {
        "en": "✗ Failed to fetch live/info bid={bid}: {err}",
        "zh": "✗ 取 live/info 失敗 bid={bid}：{err}",
    },
    "rec.not_active": {
        "en": "⚠️ bid={bid} live not active or no URL, skipping.",
        "zh": "⚠️ bid={bid} 直播未啟用或無 URL，不錄。",
    },
    "rec.ended": {
        "en": "⏹ bid={bid} live ended, {parts} part(s) total.",
        "zh": "⏹ bid={bid} 直播結束，共 {parts} 段。",
    },
    "rec.recording": {
        "en": "🔴 bid={bid} recording part {part} → {path}",
        "zh": "🔴 bid={bid} 錄第 {part} 段 → {path}",
    },
    "rec.ffmpeg_missing": {
        "en": "✗ ffmpeg not found ({ffmpeg}). Install ffmpeg or set IGLD_FFMPEG. "
        "Stopping this recording.",
        "zh": "✗ 找不到 ffmpeg（{ffmpeg}）。請安裝 ffmpeg，或用 IGLD_FFMPEG 指定路徑。停止此場錄影。",
    },
    "rec.ffmpeg_failed": {
        "en": "✗ ffmpeg failed bid={bid}: {err}",
        "zh": "✗ ffmpeg 執行失敗 bid={bid}：{err}",
    },
    "rec.max_restarts": {
        "en": "⚠️ bid={bid} hit restart limit {limit}, stopping.",
        "zh": "⚠️ bid={bid} 達重試上限 {limit}，停止。",
    },
    "rec.fast_fails": {
        "en": "⚠️ bid={bid} {count} fast failures in a row, giving up.",
        "zh": "⚠️ bid={bid} 連續 {count} 次快速失敗，放棄。",
    },
    "rec.task_error": {
        "en": "✗ recording task crashed bid={bid}: {err}",
        "zh": "✗ 錄影任務異常 bid={bid}：{err}",
    },
    # fbns
    "fbns.session_expired": {
        "en": "⚠️ IG session may be expired or needs verification — run `igld login` "
        "again. (Still retrying.)",
        "zh": "⚠️ IG session 可能已過期或被要求驗證——請重新執行 `igld login`。（仍會持續重試）",
    },
    "fbns.disconnected": {
        "en": "[fbns] disconnected: {kind}: {err}; reconnecting in {backoff}s",
        "zh": "[fbns] 連線中斷：{kind}: {err}；{backoff}s 後重連",
    },
}


def t(key: str, **kw) -> str:
    entry = MESSAGES.get(key, {})
    text = entry.get(lang()) or entry.get("en") or key
    return text.format(**kw) if kw else text
