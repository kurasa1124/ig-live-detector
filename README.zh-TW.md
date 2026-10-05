# ig-live-detector

繁體中文 | [English](README.md)

純 Python 偵測 Instagram 直播並自動錄影。偵測走 **FBNS 推播**（即時）：用 IG 登入 session 連上 Instagram 的推播通道，收到「追蹤對象開直播」的通知後，立即抓取直播串流用 `ffmpeg` 錄成 MP4。

## 需求

- Python 3.10+
- `ffmpeg`：`pip install` 會透過 `imageio-ffmpeg` 帶一份內建的；若系統已有 ffmpeg 會優先用系統的，也可用 `IGLD_FFMPEG` 指定路徑。
- 一個 IG 帳號；要收到某人的開直播推播，該帳號需 **追蹤對方並開啟直播通知**。

## 安裝

```bash
pip install git+https://github.com/kurasa1124/ig-live-detector.git
```

## 設定

用環境變數：

| 變數 | 說明 | 預設 |
|---|---|---|
| `IGLD_SETTINGS` | session 檔路徑（登入後存於此） | （必填） |
| `IGLD_OUTPUT_DIR` | 錄影輸出資料夾 | `~/.igld/recordings` |
| `IGLD_FFMPEG` | ffmpeg 執行檔 | `ffmpeg` |
| `IGLD_FILENAME` | 檔名樣板（見下） | `ig_live_{username}_{datetime}_part{part:02d}` |
| `IGLD_TARGETS` | 只錄這些帳號（username 或 uid，逗號分隔）；空＝全部 | （空） |
| `IGLD_LANG` | 訊息語言 `en` / `zh`；空＝依系統語系 | （空） |

### 檔名樣板

`IGLD_FILENAME` 可用欄位：`{username}`、`{user_id}`、`{broadcast_id}`、`{datetime}`、`{part}`（`{part:02d}` 這種格式也行）。副檔名 `.mp4` 自動加。樣板裡放 `/` 會當**子資料夾**並自動建立（如 `{username}/ig_{datetime}_part{part:02d}` → `username1/ig_..._part01.mp4`）。中斷續錄會遞增 `part`。

## 監聽哪些帳號？

FBNS 是**推播**：哪些開播通知會進來，取決於**登入帳號追蹤了誰、且開了對方的直播通知**（IG App → 對方個人頁 → 鈴鐺 → 直播視訊 ON）。

- 只監聽特定幾個帳號 → 登入帳號**只追蹤那幾個 + 開通知**（`IGLD_TARGETS` 選用）。
- 追蹤很多人、只錄其中幾個 → 設 `IGLD_TARGETS=username1,username2`，只有清單內的開播才錄。

## 使用

先登入（密碼由終端機安全輸入；帳號若開 2FA 用 `--code` 帶驗證碼或備用碼）：

```bash
export IGLD_SETTINGS=~/.igld/session.json
igld login --username <帳號> [--code 6位碼或備用碼]
```

再啟動偵測＋錄影（常駐）：

```bash
igld run
```

追蹤對象一開直播，就會自動抓串流錄成 `~/.igld/recordings/ig_live_<user>_<時間>.mp4`（可用 `IGLD_OUTPUT_DIR` 改）。

## 授權

MIT。
