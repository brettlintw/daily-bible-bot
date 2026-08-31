# CLAUDE.md — daily-bible-bot 專案說明

給任何在這個資料夾工作的 Claude Code：這是 Brett 個人維護的每日經文推播小工具，非商業專案，優先求「能動、簡單」，不要過度工程化。

## 架構：3 個獨立元件，不是單一系統

### 1. `daily_push.py` — 每日自動排程（正式運作中）
- 由 [.github/workflows/daily_push.yml](.github/workflows/daily_push.yml) 的 GitHub Actions 觸發
- Cron：`0 0 * * *`（UTC 0:00 = 台灣時間 08:00），也可在 GitHub 頁面手動 workflow_dispatch 觸發測試
- 流程：Gemini 產生經文 → 排除最近 30 筆歷史避免重複 → 推播到 LINE → 寫回 `bible_history.json`
- 跑完後 Actions 用 `git-auto-commit-action` 自動 commit `bible_history.json`，commit message 固定是 "Auto-sync bible history"
  - **這就是 commit 紀錄裡一大堆同名 commit 的來源，屬正常現象，不是異常，不需要清理**

### 2. `app.py` — LINE Webhook 被動回覆
- **部署在 Render**（Brett 本人帳號），常駐服務，不透過 GitHub Actions 執行，也不會反映在這個 repo 的 commit 紀錄裡
- 監聽 LINE 訊息，含「靈修」關鍵字時即時用 Gemini 生成一段經文回覆
- Render 免費方案有休眠機制，久未使用可能有喚醒延遲，如果 Brett 反應「Webhook 沒反應」先確認是不是冷啟動
- 支援文字指令（見 [docs/superpowers/specs/2026-07-22-line-command-console-design.md](docs/superpowers/specs/2026-07-22-line-command-console-design.md)）：`推播`、`主題 <名稱>`（僅 Brett）、`歷史 <N>`、`下載`、`選單`、`我的ID`

### 3. `main.py` — Streamlit 手動控制台
- **只在本機執行**，沒有部署到 Streamlit Cloud
- 用途：手動觸發一次推播、瀏覽/下載 `bible_history.json`（TXT/HTML 匯出）

## Secrets / 環境變數

**GitHub repo Secrets**（供 `daily_push.py` 在 Actions 裡使用）：
- `LINE_TOKEN`
- `GEMINI_API_KEY`
- `TARGET_GROUP_ID`
- `ADMIN_USER_ID`：Brett 本人的 LINE User ID，跟 Render 上的值相同。用於全部候選模型都失敗時，`daily_push.py` 主動推播失敗通知給 Brett（2026-08-31 加入，之前這個 secret 只設在 Render）。

**Render 環境變數**（供 `app.py` 使用，跟這個 repo 無關，要改去 Render 後台改）：
- `LINE_CHANNEL_SECRET`
- `LINE_TOKEN`
- `GEMINI_API_KEY`
- `TARGET_GROUP_ID`（optional）
- `ADMIN_USER_ID`：Brett 本人的 LINE User ID，用來判斷「推播」「主題」指令的權限。取得方式：在 LINE 裡打「我的ID」，機器人會回覆傳訊者的 User ID。
- `RENDER_EXTERNAL_URL`：Render 平台自動注入，不用手動設定，`app.py` 的 `/export` 路由靠這個組出對外網址。

**本機執行 `main.py`**：透過 `st.secrets` 或環境變數皆可（見 `get_secret()`）。

## 帳號歸屬
LINE 官方帳號、Google AI Studio（Gemini API）都註冊在 Brett 本人名下。API Key 過期/額度問題要提醒他去這兩個地方處理。

## Gemini 模型自動容錯

`bible_core.py` 的 `FREE_MODEL_CANDIDATES` 是一份手動維護的模型優先順序清單（依已知單價由低到高排序），`generate_verse` 在沒有指定模型時會依序嘗試，一個失敗就換下一個。

**注意**：Brett 的 Google Cloud 專案是 **Tier 1**（已開通計費，不是完全免費），Gemini API 是否收費是專案層級設定，不是依模型名稱切換——這份清單能降低「單一模型下架或出問題」造成整批失敗的風險，但無法讓呼叫變成真正免費。額度/計費狀態可以到 https://aistudio.google.com/spend 查看目前的每月支出上限與用量。

如果之後常常整批失敗（GitHub Actions/Render log 出現多行「模型 X 失敗」），除了檢查上面那個支出上限頁面，也要去 Google AI Studio 確認模型是否又被下架或改名（2026-08 曾發生 `models/gemini-2.0-flash-lite` 被下架導致整批失敗），更新這份清單的內容或順序。`GEMINI_MODEL_NAME` 環境變數已經沒有作用了（Render／GitHub Actions 上如果還留著可以不用管，但不會被讀取）。

`daily_push.py` 在所有候選模型都失敗時，會額外推一則 LINE 訊息通知 `ADMIN_USER_ID`（需要在 GitHub repo Secrets 也設定這個值，見上面「GitHub repo Secrets」清單），避免像 2026-08-31 那次一樣連續多天失敗都沒人發現。

## requirements.txt 備註
- `xhtml2pdf`：目前 `main.py`/`app.py`/`daily_push.py` **都沒有引用**，疑似遺留依賴。不要直接砍，先跟 Brett 確認是否還有計畫用到（例如匯出 PDF 功能）再移除。
- `gunicorn`：程式碼裡沒有 import 是正常的——這是 Render 上啟動 `app.py` 用的 WSGI server，屬於部署層依賴，不是程式碼層漏用。

## 已知缺口
- 沒有 `.gitignore`（`latest_group_id.txt` 目前沒被 commit，但也沒有規則明確排除它）
- 沒有任何測試
- `bible_history.json` 會持續增長，目前只在推播時 insert 到最前面，沒有輪替/封存機制
