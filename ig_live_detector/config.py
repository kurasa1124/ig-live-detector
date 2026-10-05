"""Configuration (read from environment variables)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    settings_path: str
    output_dir: str = "~/.igld/recordings"
    ffmpeg: str = "ffmpeg"
    filename_template: str = "ig_live_{username}_{datetime}_part{part:02d}"
    targets: list[str] = field(default_factory=list)
    record: bool = True
    webhook: str = ""
    webhook_token: str = ""

    @classmethod
    def from_env(cls) -> "Config":
        raw_targets = os.environ.get("IGLD_TARGETS", "").replace("\n", ",")
        record = os.environ.get("IGLD_RECORD", "1").strip().lower() not in ("0", "false", "no")
        return cls(
            settings_path=os.environ.get("IGLD_SETTINGS", "").strip(),
            output_dir=os.environ.get("IGLD_OUTPUT_DIR", "").strip()
            or "~/.igld/recordings",
            ffmpeg=os.environ.get("IGLD_FFMPEG", "ffmpeg").strip() or "ffmpeg",
            filename_template=os.environ.get("IGLD_FILENAME", "").strip()
            or "ig_live_{username}_{datetime}_part{part:02d}",
            targets=[t.strip() for t in raw_targets.split(",") if t.strip()],
            record=record,
            webhook=os.environ.get("IGLD_WEBHOOK", "").strip(),
            webhook_token=os.environ.get("IGLD_WEBHOOK_TOKEN", "").strip(),
        )
