# daily-bible-bot

每天自動生成一段聖經經文並推播到 LINE 的小工具。個人專案，非商業用途。

## 功能

- **每日自動推播**：GitHub Actions 排程每天早上 8:00（台灣時間）用 Gemini 生成一段經文，推播到指定的 LINE 群組/用戶，並避開最近 30 筆歷史內容避免重複
- **LINE Webhook 被動回覆**：在 LINE 對話裡輸入含「靈修」的訊息，即時回覆一段經文
- **手動控制台**：本機執行的 Streamlit 介面，可手動觸發推播、瀏覽並下載歷史經文紀錄（TXT/HTML）

## 架構

| 元件 | 說明 | 執行環境 |
|---|---|---|
| `daily_push.py` | 每日自動推播腳本 | GitHub Actions（排程觸發） |
| `main.py` | LINE Webhook 被動回覆 | Render（常駐服務） |
| `app.py` | 手動控制台 | 本機 Streamlit |

詳細架構、環境變數需求、已知缺口請見 [CLAUDE.md](CLAUDE.md)。

## 本機執行控制台

```bash
pip install -r requirements.txt
streamlit run app.py
```

需要環境變數：`LINE_TOKEN`、`GEMINI_API_KEY`（皆可透過 `.streamlit/secrets.toml` 或系統環境變數提供）。

## 資料

`bible_history.json` 存放所有已推播過的經文紀錄，由自動排程和手動控制台共用、共同寫入。
