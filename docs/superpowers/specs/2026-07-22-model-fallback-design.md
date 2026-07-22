# Gemini 模型自動容錯 + 手動模型選擇 — 設計文件

日期：2026-07-22
狀態：待 Brett 審閱

## 背景與目標

2026-07-22 測試 LINE 指令控制台時，`推播` 指令連續失敗，Render log 顯示：

```
ERROR:app:指令推播失敗: RetryError[<Future ... raised ResourceExhausted>]
```

`ResourceExhausted` 是 Gemini API 回報的額度用完錯誤。Brett 的 Google Cloud 帳號**沒有開通計費**，所以沒有真正的「付費模式」可以轉——所有模型都只能吃免費額度，差別只在於每個模型的免費額度寬鬆程度不同。

目標：
1. 三個進入點（`daily_push.py`、`app.py`、`main.py`）在生成經文時，自動依序嘗試多個免費模型，其中一個撞額度就換下一個，降低整體失敗機率
2. `main.py`（本機控制台）額外提供一個下拉選單，可以手動強制指定用哪一個模型（方便測試單一模型表現），或維持自動模式

## 架構：`bible_core.generate_verse` 的兩種模式

### 候選模型清單

```python
FREE_MODEL_CANDIDATES = [
    ("models/gemini-2.5-flash-lite", "額度通常較寬鬆"),
    ("models/gemini-2.0-flash-lite", "額度通常較寬鬆"),
    ("models/gemini-2.5-flash", "額度普通"),
    ("models/gemini-flash-latest", "目前預設，額度較容易撞牆"),
]
```

這份清單是依一般認知先排的順序，不是精確的即時額度數字（Google 常調整免費方案規則）。如果之後常常撞牆，可能需要調整清單順序或內容——這點會在 `CLAUDE.md` 註記提醒未來維護者。

### `generate_verse` 簽章變更

```python
def generate_verse(api_key, model_name=None, theme=None, history_limit=30):
```

- **`model_name=None`（自動模式）**：依序嘗試 `FREE_MODEL_CANDIDATES` 裡的每個模型，任何一個丟例外（不分原因）就記一行 log、換下一個；全部失敗才把最後一個例外往外拋
- **`model_name="具體字串"`（手動指定模式）**：行為跟現在一樣，只打這一個模型，搭配既有的 `_generate_with_retry`（tenacity 3 次重試）

自動模式下**不**對單一模型做 tenacity 重試——因為額度用完的錯誤重試同一個模型沒有意義，直接換下一個模型是更有效的策略；重試邏輯只保留給「手動指定單一模型」的情境（此時沒有其他候選可換，靠重試處理暫時性的網路問題比較合理）。

## `daily_push.py` / `app.py` 改動

兩者呼叫 `bible_core.generate_verse` 時都改成不傳 `model_name`（即傳 `None`），自動套用容錯清單。

**行為變更**：`GEMINI_MODEL_NAME` 這個環境變數之後不再被這兩個進入點讀取——即使 Render 或 GitHub Actions 上有設定，也不會生效了。（已與 Brett 確認可接受。）

## `main.py` 新增下拉選單

在「手動精準推送」按鈕上方：

```
選擇生成模型：
○ 自動（依序嘗試免費模型，推薦）  ← 預設選項
○ gemini-2.5-flash-lite（額度通常較寬鬆）
○ gemini-2.0-flash-lite（額度通常較寬鬆）
○ gemini-2.5-flash（額度普通）
○ gemini-flash-latest（額度較容易撞牆）
```

選單選項直接從 `bible_core.FREE_MODEL_CANDIDATES` 動態產生（含「自動」這個固定選項），避免清單改了兩邊要維護兩次。

- 選「自動」→ `bible_core.generate_verse(api_key, None, theme=chosen_theme)`
- 選特定模型 → `bible_core.generate_verse(api_key, "該模型字串", theme=chosen_theme)`

此選單只影響 `main.py` 本機手動推送，不會、也無法回頭修改 Render／GitHub Actions 上的環境變數設定。

## 錯誤處理

- 自動模式下，每個候選模型失敗時記錄一行 log：`模型 X 失敗：<原因>，改試下一個`，方便事後從 Render log／本機終端機看出是撞了哪個模型的牆
- 全部候選都失敗時的對外行為維持不變：`app.py` 回覆 LINE「⚠️ 暫時無法處理，稍後再試」；`main.py` 顯示 `st.error(...)`

## 測試方式

不引入自動化測試框架（維持個人專案一貫的作法）。手動驗證方式：用 `unittest.mock.patch` 讓候選清單前幾個模型的呼叫直接丟例外，確認 `generate_verse` 真的會往下一個模型跳、且最終仍能拿到結果（或在全部失敗時正確拋出例外）；不需要真的打 Gemini API 觸發額度限制來測試。

## 範圍外（Out of Scope）

- 不做「真正的付費模型」選項（Brett 目前沒有開通計費，之後若開通可以再開一個新 spec 處理）
- 不做動態從 Gemini API 查詢即時額度或定價的功能（目前用手動維護的固定清單）
- 下拉選單不會同步/回寫到 Render 或 GitHub Actions 的環境變數設定
