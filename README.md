# ig-live-detector

English | [繁體中文](README.zh-TW.md)

Pure-Python Instagram Live detection with auto-recording. Detection uses **FBNS push** (real-time): it connects to Instagram's push channel with an IG login session, and the moment a "followed account went live" notification arrives, it grabs the live stream and records it to MP4 with `ffmpeg`.

## Requirements

- Python 3.10+
- `ffmpeg`: `pip install` bundles one via `imageio-ffmpeg`. A system ffmpeg is preferred if present, or point to one with `IGLD_FFMPEG`.
- An IG account. To receive someone's live push, that account must **follow them and have live notifications enabled**.

## Install

```bash
pip install git+https://github.com/kurasa1124/ig-live-detector.git
```

## Configuration

Via environment variables:

| Variable | Description | Default |
|---|---|---|
| `IGLD_SETTINGS` | Session file path (saved here after login) | (required) |
| `IGLD_OUTPUT_DIR` | Recording output folder | `~/.igld/recordings` |
| `IGLD_FFMPEG` | ffmpeg executable | `ffmpeg` |
| `IGLD_FILENAME` | Filename template (see below) | `ig_live_{username}_{datetime}_part{part:02d}` |
| `IGLD_TARGETS` | Only record these accounts (username or uid, comma-separated); empty = all | (empty) |
| `IGLD_LANG` | Message language `en` / `zh`; empty = follow system locale | (empty) |

### Filename template

`IGLD_FILENAME` fields: `{username}`, `{user_id}`, `{broadcast_id}`, `{datetime}`, `{part}` (formats like `{part:02d}` work too). The `.mp4` extension is added automatically. A `/` in the template becomes a **subfolder** and is created automatically (e.g. `{username}/ig_{datetime}_part{part:02d}` → `username1/ig_..._part01.mp4`). Resuming after an interruption increments `part`.

## Which accounts does it watch?

FBNS is **push-based**: which live notifications arrive depends on **who the logged-in account follows and has live notifications enabled for** (IG App → their profile → bell → Live Videos ON).

- Watch only a few people → have the logged-in account **follow just those few + enable notifications** (`IGLD_TARGETS` optional).
- Follow many people but only record a few → set `IGLD_TARGETS=username1,username2`; only lives in the list are recorded.

## Usage

First log in (the password is read securely from the terminal; if the account has 2FA, pass a verification or backup code with `--code`):

```bash
export IGLD_SETTINGS=~/.igld/session.json
igld login --username <username> [--code 6-digit-or-backup-code]
```

Then start detection + recording (long-running):

```bash
igld run
```

When a followed account goes live, the stream is grabbed automatically and recorded to `~/.igld/recordings/ig_live_<user>_<time>.mp4` (change the folder with `IGLD_OUTPUT_DIR`).

## License

MIT.

