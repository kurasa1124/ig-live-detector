# ig-live-detector

繁體中文 | [English](README.md)

純 Python Instagram 直播通知接收器。透過 **FBNS 推播**即時接收追蹤對象的開播通知：使用 IG 登入 session 連上 Instagram 推播通道。每次收到開播通知後，依設定執行輸出：**POST webhook**，以及／或**錄製**直播串流為 MP4。接收通知是核心功能，錄影則是可選輸出。

## 需求

- Python 3.10+
- 一個 IG 帳號；要收到某人的開直播推播，該帳號需 **追蹤對方並開啟直播通知**。
- `ffmpeg`（僅錄影時需要）：`pip install` 會透過 `imageio-ffmpeg` 帶一份內建的；若系統已有 ffmpeg 會優先用系統的，也可用 `IGLD_FFMPEG` 指定路徑。

## 安裝

```bash
pip install git+https://github.com/kurasa1124/ig-live-detector.git
```

## 設定

用環境變數：

| 變數 | 說明 | 預設 |
|---|---|---|
| `IGLD_SETTINGS` | session 檔路徑（登入後存於此） | （必填） |
| `IGLD_TARGETS` | 僅對這些帳號執行動作（username 或 uid，逗號分隔）；空值＝全部 | （空） |
| `IGLD_WEBHOOK` | 收到開播通知時 POST 至此 URL；空值＝不呼叫 webhook | （空） |
| `IGLD_WEBHOOK_TOKEN` | 隨 webhook 請求以 `X-IGLD-Token` 標頭傳送 | （空） |
| `IGLD_RECORD` | 將直播錄成 MP4（設為 `0` 可停用，例如只使用 webhook） | `1` |
| `IGLD_OUTPUT_DIR` | 錄影輸出資料夾 | `~/.igld/recordings` |
| `IGLD_FFMPEG` | ffmpeg 執行檔 | `ffmpeg` |
| `IGLD_FILENAME` | 檔名樣板（見下） | `ig_live_{username}_{datetime}_part{part:02d}` |
| `IGLD_LANG` | 訊息語言 `en` / `zh`；空＝依系統語系 | （空） |

### 輸出方式

收到開播通知後，可任意組合以下輸出：

- **Webhook**（`IGLD_WEBHOOK`）：每次收到開播通知時，向設定的 URL POST JSON，內容包含 broadcast id **與播放網址**，接收端可直接使用播放網址錄影：

  ```json
  {"broadcast_id": "...", "user_id": "...", "username": "...", "status": "active", "playback_url": "https://.../master.mpd"}
  ```

  設定 `IGLD_WEBHOOK_TOKEN` 後，會以 `X-IGLD-Token` 標頭傳送。
- **錄影**（`IGLD_RECORD=1`，預設）：取得播放網址並錄製為 MP4，中斷後可續錄。

若只需接收通知並呼叫 webhook，設定 `IGLD_RECORD=0` 和 `IGLD_WEBHOOK=<url>`。

### 檔名樣板（錄影）

`IGLD_FILENAME` 可用欄位：`{username}`、`{user_id}`、`{broadcast_id}`、`{datetime}`、`{part}`（`{part:02d}` 這種格式也行）。副檔名 `.mp4` 自動加。樣板裡放 `/` 會當**子資料夾**並自動建立（如 `{username}/ig_{datetime}_part{part:02d}` → `username1/ig_..._part01.mp4`）。中斷續錄會遞增 `part`。

## 監聽哪些帳號？

FBNS 是**推播**：哪些開播通知會進來，取決於**登入帳號追蹤了誰、且開了對方的直播通知**（IG App → 對方個人頁 → 鈴鐺 → 直播視訊 ON）。

- 只監聽特定幾個帳號 → 登入帳號**只追蹤那幾個 + 開通知**（`IGLD_TARGETS` 選用）。
- 追蹤很多人、只對其中幾個執行動作 → 設 `IGLD_TARGETS=username1,username2`，只有清單內帳號的開播通知會觸發輸出。

## 使用

先登入（密碼由終端機安全輸入；帳號若開 2FA 用 `--code` 帶驗證碼或備用碼）：

```bash
export IGLD_SETTINGS=~/.igld/session.json
igld login --username <帳號> [--code 6位碼或備用碼]
```

再啟動通知接收器（常駐），透過環境變數選擇輸出方式：

```bash
# 接收開播通知並錄影（預設）
igld run

# 接收開播通知並 POST webhook，不錄影
IGLD_RECORD=0 IGLD_WEBHOOK=https://example.com/hook igld run

# 接收開播通知、錄影並 POST webhook
IGLD_WEBHOOK=https://example.com/hook igld run
```

## 授權

MIT。
