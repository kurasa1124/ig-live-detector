"""igld CLI: login (log in and save session), run (detect lives over FBNS and record)."""
from __future__ import annotations

import argparse
import getpass
import sys
from typing import Optional

from .config import Config
from .i18n import t


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(prog="igld", description=t("cli.desc"))
    sub = parser.add_subparsers(dest="cmd")

    login_p = sub.add_parser("login", help=t("cli.login.help"))
    login_p.add_argument("--username", default="", help=t("cli.login.username.help"))
    login_p.add_argument("--code", default="", help=t("cli.login.code.help"))

    sub.add_parser("run", help=t("cli.run.help"))

    args = parser.parse_args(argv)
    cfg = Config.from_env()

    if args.cmd == "login":
        if not cfg.settings_path:
            print(t("login.need_settings"))
            sys.exit(1)
        _do_login(cfg, args.username.strip(), args.code.strip())

    elif args.cmd == "run":
        if not cfg.settings_path:
            print(t("run.need_settings"))
            sys.exit(1)
        import asyncio

        from .app import InstaLiveApp

        try:
            asyncio.run(InstaLiveApp(cfg).run())
        except RuntimeError as exc:
            print(f"✗ {exc}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n" + t("run.stopped"))

    else:
        parser.print_help()


def _do_login(cfg: Config, username: str, code: str) -> None:
    """Interactive login: username -> password -> 2FA/backup code when required."""
    from . import session

    username = username or input(t("login.prompt_username")).strip()
    if not username:
        print(t("login.no_username"))
        sys.exit(1)
    password = getpass.getpass(t("login.prompt_password"))

    try:
        from instagrapi.exceptions import TwoFactorRequired
    except Exception:
        TwoFactorRequired = ()  # type: ignore

    try:
        session.login(username, password, cfg.settings_path, code)
    except TwoFactorRequired:
        code = code or input(t("login.prompt_2fa")).strip()
        if not code:
            print(t("login.no_code"))
            sys.exit(1)
        try:
            session.login(username, password, cfg.settings_path, code)
        except Exception as exc:  # noqa: BLE001
            print(t("login.failed", kind=type(exc).__name__, msg=exc))
            sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        if "out of date" in msg or "needs_upgrade" in msg:
            print(t("login.needs_upgrade"))
        else:
            print(t("login.failed", kind=type(exc).__name__, msg=msg))
        sys.exit(1)

    print(t("login.success", path=cfg.settings_path))

