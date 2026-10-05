"""Entry point for `igld run`: load config + session, run the detector (webhook / recording outputs)."""
from __future__ import annotations

from .api import run_detector
from .config import Config
from .i18n import t
from .session import load_settings


class InstaLiveApp:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.settings = load_settings(config.settings_path)
        if not self.settings:
            raise RuntimeError(t("app.no_session", path=config.settings_path))

    async def run(self) -> None:
        await run_detector(
            self.settings,
            record=self.config.record,
            webhook=self.config.webhook or None,
            webhook_token=self.config.webhook_token or None,
            output_dir=self.config.output_dir,
            ffmpeg=self.config.ffmpeg,
            filename_template=self.config.filename_template,
            targets=self.config.targets,
            on_ready=lambda: print(t("app.ready")),
        )
