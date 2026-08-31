# 模型清單修正 + 全失敗通知 — 設計文件

日期：2026-08-31
狀態：待 Brett 審閱

## 背景與目標

2026-08-31 發現 `daily_push.py` 已經連續多天推播失敗，Brett 完全沒有發現（因為失敗時只默默寫一行 log，沒有任何主動通知）。追查 GitHub Actions 的實際執行 log，發現兩個問題：

1. `models/gemini-2.0-flash-lite` 已被 Google 下架（404 Not Found），`FREE_MODEL_CANDIDATES` 清單裡還留著這個失效項目
2. Brett 的 Google Cloud 專案其實是 **Tier 1**（已開通計費），過去 28 天已經產生 NT$100.87 真實費用；先前「免費模型 A 失敗換免費模型 B」的設計前提（帳號完全免費、沒有付費層級）已經不成立——Gemini API 的計費與否是專案層級設定，不是依模型名稱切換的

Brett 已確認：知道自己在付費、想繼續保持付費換穩定；同時希望全部模型都失敗時能主動收到通知，而不是像這次一樣完全沒發現。

## 部分一：候選清單重新排序

`bible_core.FREE_MODEL_CANDIDATES` 移除已下架的 `models/gemini-2.0-flash-lite`，剩餘三個依已知單價由低到高排序（不新增模型，維持三個 flash 系列輕量模型）：

```python
FREE_MODEL_CANDIDATES = [
    ("models/gemini-2.5-flash-lite", "成本最低，優先使用"),
    ("models/gemini-flash-latest", "成本次低"),
    ("models/gemini-2.5-flash", "成本較高，當保底"),
]
```

這份排序是目前已知的相對關係，不是精確定價；Gemini 沒有公開即時查價 API 可供程式動態判斷。`generate_verse` 的自動模式邏輯（依序嘗試、任何例外就換下一個、不重試同一個候選）維持不變，只是清單內容改變。

## 部分二：全部候選失敗時，主動通知 Brett

新增 `bible_core.py` 不動，直接在 `daily_push.py` 的最外層 `except` 區塊擴充：偵測到 `bible_core.generate_verse` 拋出例外（代表所有候選模型都失敗）時，額外呼叫 `bible_core.send_line_message`，把訊息推給 `ADMIN_USER_ID`（而不是 `TARGET_GROUP_ID`）：

```
⚠️ 今日自動推播失敗
所有 Gemini 模型都無法使用，請檢查額度/計費狀態。
錯誤訊息：<原始例外內容>
```

這個通知動作本身包在自己的 `try/except` 裡——如果連通知都送不出去（例如 LINE API 也掛了），只記 log，不會讓整個 `daily_push.py` 的既有錯誤處理邏輯被打斷或重複拋錯。

需要新增讀取 `ADMIN_USER_ID` 這個環境變數（`daily_push.py` 目前沒有讀這個變數，`app.py`/Render 已經有）。**Brett 需要額外把 `ADMIN_USER_ID` 這個值也加進 GitHub repo 的 Secrets**（跟 Render 上的值相同），這是本次唯一需要 Brett 手動操作的部署步驟，會在實作計畫的最後一項列出來。

## 範圍外

- `app.py`（LINE 指令的 `推播`/`主題`）失敗時**不**額外推送通知——使用者在 LINE 對話裡已經會即時看到「⚠️ 暫時無法處理，稍後再試」的回覆，不需要重複通知
- 不新增查詢 Gemini 即時定價的功能，維持手動維護清單順序
- 不處理「如何自動偵測模型已下架」這種更進階的健康檢查機制，維持人工發現後更新清單的既有流程（`CLAUDE.md` 已有相關提醒段落）
