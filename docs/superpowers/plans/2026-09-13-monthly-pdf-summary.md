# 每月經文彙整 PDF 推播 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 每月 1 號自動把上個月的經文依主題分類彙整成一份 PDF，commit 進 repo，推播 GitHub 預覽連結到 LINE 目標群組。

**Architecture:** 新增獨立的 `monthly_summary.py` 腳本與 `.github/workflows/monthly_summary.yml` 排程，跟現有 `daily_push.yml`（每日經文）完全分開、互不影響。腳本讀取 `bible_history.json`、篩出上個月資料、依主題分組組出 HTML、用 `weasyprint` 轉成 PDF、存進 repo 並 commit、推播 LINE 連結。

**Tech Stack:** Python、`weasyprint`（新套件，HTML→PDF，靠 Ubuntu 系統的 Pango 引擎處理中文，不需要在 repo 裡管理字型檔）、GitHub Actions（`apt-get install fonts-noto-cjk` 裝系統中文字型）。沿用既有的 `bible_core.load_history`、`bible_core.send_line_message`、`bible_core.THEMES`。

## Global Constraints

- 個人小專案，不引入 pytest 或任何自動化測試框架；驗證用 `unittest.mock`，且**不對 `weasyprint` 做本機真實渲染測試**——因為它需要 Linux 圖形函式庫，在 Windows 開發機上裝不起來、無法本機驗證，所有跟 `weasyprint` 實際渲染有關的程式碼路徑，驗證時一律用 mock 取代，真正的端到端驗證要靠 GitHub Actions 的 `workflow_dispatch`（人工執行，見 Task 4）
- **不使用 `xhtml2pdf`**——已實測證實它無法正確嵌入中文字型（渲染出來是黑色方塊），這是已驗證過的結論，不要重新嘗試這條路
- PDF 內容依主題分組顯示（依 `bible_core.THEMES` 既有順序，當月沒有出現的主題不顯示空區塊），同一主題內的經文依日期由舊到新排列
- `render_pdf`（呼叫 `weasyprint` 的函式）裡才 `from weasyprint import HTML`（延遲匯入，不要放在檔案最上面）——這樣即使本機沒有 `weasyprint` 執行環境，`import monthly_summary` 跟其他函式的手動驗證都不會因為匯入失敗而整個掛掉
- 上個月完全沒有推播紀錄時，直接跳過，不產生 PDF、不推播、不報錯
- PDF 產生或推播失敗只記 log，不串接管理員 LINE 告警機制（這是錦上添花功能，不是核心每日推播）
- 所有使用者可見文字、log 訊息維持繁體中文

---

## Task 1: `monthly_summary.py` — 核心邏輯（日期範圍、篩選、主題分組、HTML）

**Files:**
- Create: `monthly_summary.py`

**Interfaces:**
- Produces：
  - `get_previous_month_range(today=None) -> tuple[str, str, str]`：回傳 `(該月第一天日期字串, 該月最後一天日期字串, "YYYY-MM"標籤)`
  - `filter_monthly_entries(all_history, start_str, end_str) -> list[dict]`：篩出日期落在區間內的紀錄，依 `(date, time)` 由舊到新排序
  - `group_by_theme(monthly_data) -> list[tuple[str, list[dict]]]`：依 `bible_core.THEMES` 順序分組，回傳 `[(主題名稱, 該主題底下的紀錄列表), ...]`，跳過當月沒有出現的主題
  - `build_grouped_html(monthly_data, label) -> str`：組出完整 HTML 字串（含主題標題區塊）
  - `render_pdf(html_content, output_path) -> None`：內部才 `import weasyprint`，把 HTML 轉成 PDF 存檔
  - `main() -> None`：整合以上流程，含讀取環境變數、呼叫 `bible_core.load_history`/`send_line_message`

- [ ] **Step 1: 寫 `monthly_summary.py`**

```python
import os
import logging
from datetime import datetime, timedelta
import bible_core

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

REPO_BLOB_BASE = "https://github.com/brettlintw/daily-bible-bot/blob/main"


def get_previous_month_range(today=None):
    today = today or datetime.now(bible_core.TZ_TW)
    first_of_this_month = today.replace(day=1)
    last_of_prev_month = first_of_this_month - timedelta(days=1)
    prev_year, prev_month = last_of_prev_month.year, last_of_prev_month.month
    start_str = f"{prev_year:04d}-{prev_month:02d}-01"
    end_str = f"{prev_year:04d}-{prev_month:02d}-{last_of_prev_month.day:02d}"
    label = f"{prev_year:04d}-{prev_month:02d}"
    return start_str, end_str, label


def filter_monthly_entries(all_history, start_str, end_str):
    monthly_data = [e for e in all_history if start_str <= e.get("date", "") <= end_str]
    return sorted(monthly_data, key=lambda e: (e.get("date", ""), e.get("time", "")))


def group_by_theme(monthly_data):
    groups = {}
    for entry in monthly_data:
        theme = entry.get("category", "").rsplit("-", 1)[-1] or "未分類"
        groups.setdefault(theme, []).append(entry)
    ordered_themes = [t for t in bible_core.THEMES if t in groups]
    extra_themes = [t for t in groups if t not in bible_core.THEMES]
    return [(theme, groups[theme]) for theme in ordered_themes + extra_themes]


def build_grouped_html(monthly_data, label):
    grouped = group_by_theme(monthly_data)
    html_content = f"""<html><head><meta charset="utf-8">
    <style>body {{ font-family: sans-serif; font-size: 16px; line-height: 1.6; padding: 20px; }}
    h1 {{ font-size: 22px; }}
    h2 {{ font-size: 18px; border-bottom: 2px solid #888; padding-bottom: 4px; margin-top: 30px; }}
    .entry {{ border-bottom: 1px solid #ccc; margin-bottom: 20px; padding-bottom: 10px; }}
    .meta {{ color: #555; font-size: 14px; }}</style></head><body>
    <h1>{label} 靈修經文彙整（依主題分類）</h1>"""
    for theme, entries in grouped:
        html_content += f"<h2>{theme}（{len(entries)} 筆）</h2>"
        for h in entries:
            content = h.get('content', '無內容').replace('\n', '<br/>')
            html_content += f"<div class='entry'><div class='meta'>{h.get('date')} {h.get('time')} | {h.get('category')}</div><div>{content}</div></div>"
    html_content += "</body></html>"
    return html_content


def render_pdf(html_content, output_path):
    from weasyprint import HTML
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    HTML(string=html_content).write_pdf(output_path)


def main():
    target_id = os.environ.get('TARGET_GROUP_ID', '').strip()
    line_token = os.environ.get('LINE_TOKEN', '').strip()

    if not all([target_id, line_token]):
        return

    start_str, end_str, label = get_previous_month_range()
    monthly_data = filter_monthly_entries(bible_core.load_history(), start_str, end_str)

    if not monthly_data:
        logger.info(f"{label} 沒有任何推播紀錄，跳過")
        return

    output_path = f"monthly_summaries/{label}.pdf"
    html_content = build_grouped_html(monthly_data, label)

    try:
        render_pdf(html_content, output_path)
    except Exception as e:
        logger.error(f"PDF 產生失敗: {e}")
        return

    repo_url = f"{REPO_BLOB_BASE}/{output_path}"
    try:
        bible_core.send_line_message(line_token, target_id, f"📖 {label} 經文彙整已產生\n{repo_url}")
    except Exception as e:
        logger.error(f"推播失敗: {e}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 手動驗證 `get_previous_month_range` 與 `filter_monthly_entries`（純邏輯，不需要 `weasyprint`）**

Run:
```bash
python -c "
import monthly_summary
from datetime import datetime, timezone, timedelta

TZ_TW = timezone(timedelta(hours=8))

fake_today = datetime(2026, 9, 13, tzinfo=TZ_TW)
print('情境一:', monthly_summary.get_previous_month_range(fake_today))

fake_jan = datetime(2026, 1, 5, tzinfo=TZ_TW)
print('情境二（跨年份 12 月）:', monthly_summary.get_previous_month_range(fake_jan))

fake_history = [
    {'date': '2026-08-05', 'time': '10:00:00', 'category': '自動靈修-智慧', 'content': 'A'},
    {'date': '2026-07-31', 'time': '10:00:00', 'category': '手動-平安', 'content': 'B'},
    {'date': '2026-08-20', 'time': '09:00:00', 'category': '指令-智慧', 'content': 'C'},
    {'date': '2026-09-01', 'time': '10:00:00', 'category': '自動靈修-喜樂', 'content': 'D'},
]
result = monthly_summary.filter_monthly_entries(fake_history, '2026-08-01', '2026-08-31')
print('情境三 filter 結果 (應為 A, C，依日期排序):', [e['content'] for e in result])

empty_result = monthly_summary.filter_monthly_entries(fake_history, '2026-06-01', '2026-06-30')
print('情境四（空月份）:', empty_result)
"
```

Expected:
```
情境一: ('2026-08-01', '2026-08-31', '2026-08')
情境二（跨年份 12 月）: ('2025-12-01', '2025-12-31', '2025-12')
情境三 filter 結果 (應為 A, C，依日期排序): ['A', 'C']
情境四（空月份）: []
```

- [ ] **Step 3: 手動驗證 `group_by_theme` 與 `build_grouped_html`**

Run:
```bash
python -c "
import monthly_summary

fake_data = [
    {'date': '2026-08-01', 'time': '10:00', 'category': '自動靈修-智慧', 'content': 'A'},
    {'date': '2026-08-05', 'time': '10:00', 'category': '手動-平安', 'content': 'B'},
    {'date': '2026-08-10', 'time': '10:00', 'category': '指令-智慧', 'content': 'C'},
]
grouped = monthly_summary.group_by_theme(fake_data)
print('分組結果:', [(theme, [e['content'] for e in entries]) for theme, entries in grouped])

html = monthly_summary.build_grouped_html(fake_data, '2026-08')
wisdom_pos = html.find('智慧（2 筆）')
peace_pos = html.find('平安（1 筆）')
print('智慧標題有出現:', wisdom_pos != -1)
print('平安標題有出現:', peace_pos != -1)
print('智慧區塊在平安區塊前面:', wisdom_pos < peace_pos)
print('沒出現的主題（例如信心）不該出現:', '信心（' not in html)
"
```

Expected:
```
分組結果: [('智慧', ['A', 'C']), ('平安', ['B'])]
智慧標題有出現: True
平安標題有出現: True
智慧區塊在平安區塊前面: True
沒出現的主題（例如信心）不該出現: True
```

（`bible_core.THEMES` 目前順序是安慰、力量、盼望、智慧、愛與饒恕、平安、信心...，智慧排在平安前面，所以分組結果跟 HTML 裡的區塊順序都應該是智慧在前。）

- [ ] **Step 4: 手動驗證 `main()` 整合流程（mock 掉 `render_pdf`，完全不觸碰真實 `weasyprint`）**

Run:
```bash
python -c "
import os
os.environ['TARGET_GROUP_ID'] = 'Cdummygroup'
os.environ['LINE_TOKEN'] = 'dummy'
import monthly_summary
import bible_core
from unittest.mock import patch

fake_history = [
    {'date': '2026-08-05', 'time': '10:00:00', 'category': '自動靈修-智慧', 'content': 'A'},
]

with patch.object(bible_core, 'load_history', return_value=fake_history), \
     patch.object(monthly_summary, 'get_previous_month_range', return_value=('2026-08-01', '2026-08-31', '2026-08')), \
     patch.object(monthly_summary, 'render_pdf') as render_mock, \
     patch.object(bible_core, 'send_line_message') as send_mock:
    monthly_summary.main()
    print('render_pdf 呼叫次數:', render_mock.call_count)
    print('render_pdf 第二個參數（輸出路徑）:', render_mock.call_args[0][1])
    print('send_line_message 呼叫參數:', send_mock.call_args)

# 情境二：上個月完全沒有資料 -> 不該呼叫 render_pdf 或 send_line_message
with patch.object(bible_core, 'load_history', return_value=[]), \
     patch.object(monthly_summary, 'get_previous_month_range', return_value=('2026-08-01', '2026-08-31', '2026-08')), \
     patch.object(monthly_summary, 'render_pdf') as render_mock2, \
     patch.object(bible_core, 'send_line_message') as send_mock2:
    monthly_summary.main()
    print('情境二 render_pdf 呼叫次數（應為 0）:', render_mock2.call_count)
    print('情境二 send_line_message 呼叫次數（應為 0）:', send_mock2.call_count)
"
```

Expected:
```
render_pdf 呼叫次數: 1
render_pdf 第二個參數（輸出路徑）: monthly_summaries/2026-08.pdf
send_line_message 呼叫參數: call('dummy', 'Cdummygroup', '📖 2026-08 經文彙整已產生\nhttps://github.com/brettlintw/daily-bible-bot/blob/main/monthly_summaries/2026-08.pdf')
情境二 render_pdf 呼叫次數（應為 0）: 0
情境二 send_line_message 呼叫次數（應為 0）: 0
```

- [ ] **Step 5: 手動驗證語法**

Run: `python -m py_compile monthly_summary.py`
Expected: 沒有任何輸出。

- [ ] **Step 6: Commit**

```bash
git add monthly_summary.py
git commit -m "feat: add monthly_summary.py for theme-grouped PDF digest"
```

---

## Task 2: `requirements.txt` + `.github/workflows/monthly_summary.yml`

**Files:**
- Modify: `requirements.txt`
- Create: `.github/workflows/monthly_summary.yml`

**Interfaces:** 無新的程式介面，純設定檔

- [ ] **Step 1: 在 `requirements.txt` 加入 `weasyprint`**

原本（`requirements.txt`）：
```
# Web 框架與部署
flask
gunicorn

# LINE 開發工具
line-bot-sdk

# AI 核心功能
google-generativeai

# 穩定性與重試機制
tenacity
streamlit
xhtml2pdf
```

換成：
```
# Web 框架與部署
flask
gunicorn

# LINE 開發工具
line-bot-sdk

# AI 核心功能
google-generativeai

# 穩定性與重試機制
tenacity
streamlit
xhtml2pdf

# 每月經文彙整 PDF（monthly_summary.py 用，需要系統 Pango 引擎，只在 Linux 上能正常運作）
weasyprint
```

（`xhtml2pdf` 維持不動——它本來就在檔案裡且未被使用，這次也沒用到它，不代表要移除，是否移除留給 Brett 之後決定。）

- [ ] **Step 2: 新增 `.github/workflows/monthly_summary.yml`**

```yaml
name: Monthly Summary

on:
  schedule:
    - cron: '0 1 1 * *'
  workflow_dispatch: # 允許在 GitHub 頁面手動點擊執行測試

jobs:
  monthly_summary_job:
    runs-on: ubuntu-latest
    permissions:
      contents: write # 必須授予寫入權限，否則無法進行自動提交

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install system CJK font
        run: sudo apt-get update && sudo apt-get install -y fonts-noto-cjk

      - name: Install dependencies
        run: pip install line-bot-sdk weasyprint

      - name: Run Python Script
        env:
          LINE_TOKEN: ${{ secrets.LINE_TOKEN }}
          TARGET_GROUP_ID: ${{ secrets.TARGET_GROUP_ID }}
        run: python monthly_summary.py

      - name: Auto-Commit Changes
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "Auto-generate monthly summary PDF"
          file_pattern: 'monthly_summaries/*.pdf'
```

（`LINE_TOKEN`、`TARGET_GROUP_ID` 這兩個 GitHub Secrets 已經存在（`daily_push.yml` 本來就在用），不需要新增任何 Secret。）

- [ ] **Step 3: 驗證 YAML 語法**

Run:
```bash
python -c "
import yaml
with open('.github/workflows/monthly_summary.yml', encoding='utf-8') as f:
    data = yaml.safe_load(f)
print('YAML 語法正確，job 名稱:', list(data['jobs'].keys()))
"
```
Expected:
```
YAML 語法正確，job 名稱: ['monthly_summary_job']
```

- [ ] **Step 4: Commit**

```bash
git add requirements.txt .github/workflows/monthly_summary.yml
git commit -m "feat: add monthly_summary GitHub Actions workflow"
```

---

## Task 3: 更新 `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:** 無（純文件更新）

- [ ] **Step 1: 在「架構：3 個獨立元件，不是單一系統」這節後面，新增第 4 個元件說明**

在 `CLAUDE.md` 的「### 3. `main.py` — Streamlit 手動控制台」這段之後、「## Secrets / 環境變數」這個標題之前，插入：

```markdown
### 4. `monthly_summary.py` — 每月經文彙整 PDF（2026-09 新增）
- 由 [.github/workflows/monthly_summary.yml](.github/workflows/monthly_summary.yml) 的 GitHub Actions 觸發，跟 `daily_push.yml` 完全獨立的排程
- Cron：`0 1 1 * *`（每月 1 號 UTC 01:00 = 台灣時間 09:00），也可手動 workflow_dispatch 觸發測試
- 流程：讀 `bible_history.json` → 篩出上個月資料 → 依主題分組（`bible_core.THEMES` 順序）→ 用 `weasyprint` 轉成 PDF → 存到 `monthly_summaries/YYYY-MM.pdf` 並 commit → 推播 GitHub 網頁預覽連結到 LINE 目標群組
- 用 `weasyprint`（不是 `xhtml2pdf`——已實測 `xhtml2pdf` 無法正確嵌入中文字型），需要 GitHub Actions 的 Ubuntu 環境裝 `fonts-noto-cjk` 系統字型，本機 Windows 無法完整測試這個流程的 PDF 渲染結果
- 上個月沒有推播紀錄時直接跳過，不報錯、不通知
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document monthly_summary.py PDF digest feature"
```

---

## Task 4（人工執行，非 subagent）：Brett 手動驗證真實 PDF 渲染

這個任務需要在 GitHub Actions 的 Ubuntu 環境裡才能真正驗證 `weasyprint` 的中文渲染結果，本機 Windows 無法測試，必須由 Brett 本人（或有 repo 存取權的人）完成。

- [ ] Push 所有 commit 到 GitHub
- [ ] 到 GitHub Actions 頁面，找到「Monthly Summary」這個 workflow，手動點擊「Run workflow」觸發一次
- [ ] 確認執行成功（綠色勾勾），檢查 log 有沒有出現「沒有任何推播紀錄，跳過」（如果上個月剛好沒資料，這是正常情況，不算失敗）
- [ ] 如果真的有產生 PDF：到 repo 裡 `monthly_summaries/` 資料夾確認檔案存在，點開 GitHub 內建的 PDF 預覽，**人工確認中文有沒有正常顯示**（這是本次唯一沒辦法在本機先驗證過的部分）
- [ ] 確認有收到 LINE 訊息，連結點開能正常看到 PDF 內容
- [ ] 確認 PDF 內容真的是按主題分區塊，不是按日期條列

## Self-Review Notes

**Spec coverage：** 依主題分組（不按日期）✅（Task 1 `group_by_theme`/`build_grouped_html`），改用 `weasyprint` 不用 `xhtml2pdf` ✅（Task 1 `render_pdf` + Task 2 requirements.txt），GitHub Actions 裝系統中文字型 ✅（Task 2 workflow `apt-get install fonts-noto-cjk`），PDF 存 repo + GitHub 預覽連結推播 ✅（Task 1 `main()` + Task 2 workflow auto-commit），上個月無資料時跳過 ✅（Task 1 `main()` 的 `if not monthly_data`），失敗不觸發管理員告警 ✅（未新增任何告警邏輯），CLAUDE.md 記錄 ✅（Task 3），Brett 手動驗證真實渲染 ✅（Task 4）。

**Type consistency：** `get_previous_month_range`、`filter_monthly_entries`、`group_by_theme`、`build_grouped_html`、`render_pdf` 的函式簽章在 Task 1 定義、`main()` 呼叫端一致；`render_pdf` 延遲匯入 `weasyprint` 這件事在 Global Constraints 跟 Task 1 的程式碼裡都一致強調，避免手動驗證時因為本機沒有 `weasyprint` 執行環境而整個測試腳本掛掉。
