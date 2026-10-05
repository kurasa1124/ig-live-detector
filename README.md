# ig-live-detector

English | [繁體中文](README.zh-TW.md)

Pure-Python Instagram Live notification receiver. It receives live notifications for followed accounts in real time via **FBNS push**, connecting to Instagram's push channel with an IG login session. On each received live notification it runs the outputs you configure: **POST a webhook** and/or **record** the stream to MP4. Receiving notifications is the core; recording is just one optional output.

## Requirements

- Python 3.10+
- An IG account. To receive someone's live push, that account must **follow them and have live notifications enabled**.
- `ffmpeg` (only when recording): `pip install` bundles one via `imageio-ffmpeg`. A system ffmpeg is preferred if present, or point to one with `IGLD_FFMPEG`.

## Install

```bash
pip install git+https://github.com/kurasa1124/ig-live-detector.git
```

## Configuration

Via environment variables:

| Variable | Description | Default |
|---|---|---|
| `IGLD_SETTINGS` | Session file path (saved here after login) | (required) |
| `IGLD_SETTINGS_JSON` | Session JSON content; on first run it is written to `IGLD_SETTINGS` when that file is missing (for server deploys) | (empty) |
| `IGLD_TARGETS` | Only act on these accounts (username or uid, comma-separated); empty = all | (empty) |
| `IGLD_WEBHOOK` | On each received live notification, POST to this URL; empty = no webhook | (empty) |
| `IGLD_WEBHOOK_TOKEN` | Sent as the `X-IGLD-Token` header with the webhook | (empty) |
| `IGLD_RECORD` | Record the stream to MP4 (`0` to disable, e.g. webhook-only) | `1` |
| `IGLD_OUTPUT_DIR` | Recording output folder | `~/.igld/recordings` |
| `IGLD_FFMPEG` | ffmpeg executable | `ffmpeg` |
| `IGLD_FILENAME` | Filename template (see below) | `ig_live_{username}_{datetime}_part{part:02d}` |
| `IGLD_LANG` | Message language `en` / `zh`; empty = follow system locale | (empty) |

### Outputs

After receiving a live notification, pick any combination of outputs:

- **Webhook** (`IGLD_WEBHOOK`) — on each received live notification, POST JSON to the URL with the broadcast id **and the playback URL** (so the receiver can record directly):

  ```json
  {"broadcast_id": "...", "user_id": "...", "username": "...", "status": "active", "playback_url": "https://.../master.mpd"}
  ```

  If `IGLD_WEBHOOK_TOKEN` is set, it's sent as the `X-IGLD-Token` header.
- **Recording** (`IGLD_RECORD=1`, default) — fetch the playback URL and record to MP4 (with resume on interruption).

To receive notifications and send webhooks without recording, set `IGLD_RECORD=0` and `IGLD_WEBHOOK=<url>`.

### Filename template (recording)

`IGLD_FILENAME` fields: `{username}`, `{user_id}`, `{broadcast_id}`, `{datetime}`, `{part}` (formats like `{part:02d}` work too). The `.mp4` extension is added automatically. A `/` in the template becomes a **subfolder** and is created automatically (e.g. `{username}/ig_{datetime}_part{part:02d}` → `username1/ig_..._part01.mp4`). Resuming after an interruption increments `part`.

## Which accounts does it watch?

FBNS is **push-based**: which live notifications arrive depends on **who the logged-in account follows and has live notifications enabled for** (IG App → their profile → bell → Live Videos ON).

- Watch only a few people → have the logged-in account **follow just those few + enable notifications** (`IGLD_TARGETS` optional).
- Follow many but act on only a few → set `IGLD_TARGETS=username1,username2`; only lives in the list are acted on.

## Usage

### 1. Produce a session (local login)

`igld login` saves a session to `IGLD_SETTINGS`:

```bash
export IGLD_SETTINGS=~/.igld/session.json
igld login --username <username>
```

The password is read from the terminal; for a 2FA account a 6-digit or backup code is prompted (or passed with `--code`).

### 2. Run (receive notifications)

Long-running. Outputs are chosen via env:

```bash
# receive live notifications + record (default)
igld run

# receive live notifications → POST a webhook, no recording
IGLD_RECORD=0 IGLD_WEBHOOK=https://example.com/hook igld run

# receive live notifications → record AND POST a webhook
IGLD_WEBHOOK=https://example.com/hook igld run
```

### 3. Deploy to a server

`igld run` uses an existing session, produced locally with `igld login`. To provide it:

1. Read the local session:

   ```bash
   cat ~/.igld/session.json
   ```

2. On the server set:
   - `IGLD_SETTINGS=/data/session.json` — a writable path, ideally on a persistent volume.
   - `IGLD_SETTINGS_JSON=<the full JSON from step 1>`.

On first start the session is written to `IGLD_SETTINGS` from `IGLD_SETTINGS_JSON` and reused on every restart. Update `IGLD_SETTINGS_JSON` after logging in again locally when the session expires.

## License

MIT.

