# LINE 指令控制台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓 Brett 能直接在 LINE 對話裡打文字指令（推播/主題/歷史/下載/選單），操作現有的每日經文推播機器人，不需要另開網頁或碰電腦。

**Architecture:** 把 `daily_push.py`、`main.py` 現有重複的「生成經文/推播/讀寫歷史/產生 HTML 備份」邏輯抽成共用模組 `bible_core.py`；新增純函式模組 `command_parser.py` 負責解析 LINE 文字指令（不含任何外部依賴，方便獨立驗證）；`app.py`（已部署在 Render）整合兩者，新增指令判斷、權限檢查、`/export` 路由與 Quick Reply 選單。`daily_push.py` 與 `main.py` 改為呼叫 `bible_core`，行為不變。

**Tech Stack:** Python 3.9、Flask（app.py 既有）、`linebot`（v2 SDK，`from linebot import LineBotApi` 那個版本，非 `linebot.v3`）、`google-generativeai`、`tenacity`。不新增任何套件。

## Global Constraints

- 個人小專案，不引入 pytest 或任何自動化測試框架；每個任務的驗證一律用「執行一段指令、比對輸出」的手動方式，且不得依賴真實的 `LINE_TOKEN`/`GEMINI_API_KEY`（用假字串即可，只驗證邏輯路徑，不觸發真實網路呼叫）
- `bible_core.py` 統一使用 `linebot`（v2 SDK：`LineBotApi` + `TextSendMessage`），因為 `app.py` 已經用這套；`main.py` 原本用的是 `linebot.v3.messaging`（`Configuration`/`ApiClient`/`MessagingApi`），改用 `bible_core` 之後等於從 v3 換回 v2，對外行為（推播成功與否）不變
- 所有使用者可見的文字（回覆訊息、錯誤提示）維持繁體中文，語氣與既有程式碼一致（沿用 `⚠️`、`✅` 等既有 emoji 標記風格）
- 不新增 `requirements.txt` 套件——全部功能用現有的 `flask`、`line-bot-sdk`、`google-generativeai`、`tenacity` 就能完成
- `歷史 <N>` 的 N 必須是正整數；非數字、0、負數一律視為格式錯誤
- `推播`、`主題 <名稱>` 僅限 `ADMIN_USER_ID` 可觸發；`歷史`、`下載`、`選單`、`我的ID`、`靈修` 所有人可用

---

## Task 1: 建立共用模組 `bible_core.py`

**Files:**
- Create: `bible_core.py`

**Interfaces:**
- Produces：
  - `bible_core.DB_FILE: str`、`bible_core.ID_FILE: str`、`bible_core.THEMES: list[str]`
  - `bible_core.load_history(db_file=DB_FILE) -> list[dict]`
  - `bible_core.append_history(entry: dict, db_file=DB_FILE) -> list[dict]`
  - `bible_core.record_entry(payload: str, category: str) -> dict`
  - `bible_core.generate_verse(api_key: str, model_name: str, theme: str | None = None, history_limit: int = 30) -> tuple[str, str]`（回傳 `(經文內容, 實際使用的主題)`）
  - `bible_core.send_line_message(line_token: str, target_id: str, message_text: str) -> None`
  - `bible_core.generate_html_backup(data: list[dict]) -> str`

- [ ] **Step 1: 寫 `bible_core.py`**

```python
import os
import json
import random
import logging
from datetime import datetime, timezone, timedelta

import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

TZ_TW = timezone(timedelta(hours=8))
DB_FILE = "bible_history.json"
ID_FILE = "latest_group_id.txt"
THEMES = ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"]


def load_history(db_file=DB_FILE):
    if os.path.exists(db_file):
        with open(db_file, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []


def append_history(entry, db_file=DB_FILE):
    data = load_history(db_file)
    data.insert(0, entry)
    with open(db_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return data


def record_entry(payload, category):
    entry = {
        "date": datetime.now(TZ_TW).strftime("%Y-%m-%d"),
        "time": datetime.now(TZ_TW).strftime("%H:%M:%S"),
        "category": category,
        "content": payload,
    }
    append_history(entry)
    return entry


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def _generate_with_retry(model, prompt):
    return model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.8))


def generate_verse(api_key, model_name, theme=None, history_limit=30):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    chosen_theme = theme or random.choice(THEMES)
    history_titles = [item.get("content", "")[:60] for item in load_history()[:history_limit]]
    history_str = "\n".join(history_titles)

    prompt = f"""
    你是一位充滿智慧的資深牧者。
    請精選一段聖經經文。
    主題選擇：{chosen_theme}。

    【絕對禁令】：嚴禁輸出與下方清單相似或重複的內容。
    這是一份你最近分享過的內容清單 (請避開以下所有內容)：
    {history_str}

    請依照此格式嚴格輸出：
    【內容】；【章節】；【領受】。
    """

    res = _generate_with_retry(model, prompt)
    return res.text.strip(), chosen_theme


def send_line_message(line_token, target_id, message_text):
    line_api = LineBotApi(line_token)
    line_api.push_message(target_id, TextSendMessage(text=message_text))


def generate_html_backup(data):
    html_content = """<html><head><meta charset="utf-8">
    <style>body { font-family: sans-serif; font-size: 16px; line-height: 1.6; padding: 20px; }
    .entry { border-bottom: 1px solid #ccc; margin-bottom: 20px; padding-bottom: 10px; }
    .meta { color: #555; font-size: 14px; }</style></head><body>
    <h1>靈修歷史紀錄備份</h1>"""
    for h in data:
        content = h.get('content', '無內容').replace('\n', '<br/>')
        html_content += f"<div class='entry'><div class='meta'>{h.get('date')} {h.get('time')} | {h.get('category')}</div><div>{content}</div></div>"
    html_content += "</body></html>"
    return html_content
```

- [ ] **Step 2: 手動驗證（不需要真實 API Key）**

Run:
```bash
python -c "
import bible_core
print('load_history:', bible_core.load_history())
html = bible_core.generate_html_backup([{'date': '2026-01-01', 'time': '08:00:00', 'category': 'test', 'content': 'test content'}])
print('html starts with:', html[:20])
entry = bible_core.record_entry('測試經文', '測試分類')
print('record_entry returned:', entry)
print('history now:', bible_core.load_history()[:1])
"
```

Expected:
```
load_history: []
html starts with: <html><head><meta
record_entry returned: {'date': '...', 'time': '...', 'category': '測試分類', 'content': '測試經文'}
history now: [{'date': '...', 'time': '...', 'category': '測試分類', 'content': '測試經文'}]
```

執行完後手動刪掉這次測試寫入 `bible_history.json` 的那筆測試資料（或直接 `git checkout -- bible_history.json` 還原，因為這步只是驗證邏輯，不是真的要留紀錄）。

- [ ] **Step 3: Commit**

```bash
git checkout -- bible_history.json
git add bible_core.py
git commit -m "feat: extract shared bible_core module"
```

---

## Task 2: `daily_push.py` 改用 `bible_core`

**Files:**
- Modify: `daily_push.py`（整份重寫，原本 84 行的重複邏輯改成呼叫 `bible_core`）

**Interfaces:**
- Consumes：Task 1 的 `bible_core.generate_verse`、`bible_core.send_line_message`、`bible_core.record_entry`、`bible_core.ID_FILE`

- [ ] **Step 1: 重寫 `daily_push.py`**

```python
import os
import logging
import bible_core

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    target_id = os.environ.get('TARGET_GROUP_ID', '').strip()
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    line_token = os.environ.get('LINE_TOKEN', '').strip()
    model_name = os.environ.get('GEMINI_MODEL_NAME', 'models/gemini-flash-latest')

    if not all([target_id, api_key, line_token]):
        return

    with open(bible_core.ID_FILE, "w") as f:
        f.write(target_id)

    try:
        payload, chosen_theme = bible_core.generate_verse(api_key, model_name)
        bible_core.send_line_message(line_token, target_id, f'【每日靈修】\n\n{payload}')
        bible_core.record_entry(payload, f"自動靈修-{chosen_theme}")
    except Exception as e:
        logger.error(f"系統錯誤: {e}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 手動驗證語法**

Run: `python -m py_compile daily_push.py`
Expected: 沒有任何輸出（代表語法正確），且不需要設定任何環境變數就能通過，因為 `py_compile` 只檢查語法，不會真的執行 `main()`。

- [ ] **Step 3: Commit**

```bash
git add daily_push.py
git commit -m "refactor: daily_push.py uses bible_core"
```

---

## Task 3: `main.py` 改用 `bible_core`

**Files:**
- Modify: `main.py:1-95`（移除自帶的 `load_history`、`generate_html_backup`、`send_line_message`、`generate_with_retry` 與相關 import，改呼叫 `bible_core`；`get_secret` 與 Streamlit UI 邏輯保留不動）

**Interfaces:**
- Consumes：Task 1 的 `bible_core.load_history`、`bible_core.generate_html_backup`、`bible_core.generate_verse`、`bible_core.send_line_message`、`bible_core.record_entry`

- [ ] **Step 1: 修改 `main.py` 開頭 import 與移除的函式**

把原本檔案開頭到 `send_line_message` 函式為止的內容：

```python
import streamlit as st
import json
import os
import random
import google.generativeai as genai
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, TextMessage
from datetime import datetime, timezone, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential
from itertools import groupby
import io

# --- 1. 設定區 ---
DB_FILE = "bible_history.json"
ID_FILE = "latest_group_id.txt"
TZ_TW = timezone(timedelta(hours=8))
DEFAULT_TARGET_ID = "C8a7777fb460a7ca0479b1b33c82f7a16"

st.set_page_config(page_title="靈修控制台", layout="wide")
st.title("🛡️ 聖經-LINE推送 V60.5 正式版")

# --- 輔助函式 ---
def load_history():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return []
    return []

# 產生穩定的 HTML 備份內容
def generate_html_backup(data):
    html_content = """<html><head><meta charset="utf-8">
    <style>body { font-family: sans-serif; font-size: 16px; line-height: 1.6; padding: 20px; }
    .entry { border-bottom: 1px solid #ccc; margin-bottom: 20px; padding-bottom: 10px; }
    .meta { color: #555; font-size: 14px; }</style></head><body>
    <h1>靈修歷史紀錄備份</h1>"""
    for h in data:
        content = h.get('content', '無內容').replace('\n', '<br/>')
        html_content += f"<div class='entry'><div class='meta'>{h.get('date')} {h.get('time')} | {h.get('category')}</div><div>{content}</div></div>"
    html_content += "</body></html>"
    return html_content

def get_secret(key_name):
    return st.secrets.get(key_name, os.environ.get(key_name, ""))

# --- [v3] 封裝推送函式 ---
def send_line_message(target_id, message_text):
    configuration = Configuration(access_token=get_secret("LINE_TOKEN"))
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.push_message(
            PushMessageRequest(
                to=target_id,
                messages=[TextMessage(text=message_text)]
            )
        )
```

換成：

```python
import streamlit as st
import os
import bible_core
from datetime import datetime
from itertools import groupby

# --- 1. 設定區 ---
DEFAULT_TARGET_ID = "C8a7777fb460a7ca0479b1b33c82f7a16"

st.set_page_config(page_title="靈修控制台", layout="wide")
st.title("🛡️ 聖經-LINE推送 V60.5 正式版")

# --- 輔助函式 ---
def get_secret(key_name):
    return st.secrets.get(key_name, os.environ.get(key_name, ""))
```

- [ ] **Step 2: 修改「系統自動配置」區塊裡讀 `ID_FILE` 的地方**

原本：
```python
if os.path.exists(ID_FILE):
    with open(ID_FILE, "r") as f:
```

換成：
```python
if os.path.exists(bible_core.ID_FILE):
    with open(bible_core.ID_FILE, "r") as f:
```

- [ ] **Step 3: 移除 `generate_with_retry`，修改「手動精準推送」按鈕邏輯**

原本：
```python
# --- 3. 靈修推送核心邏輯 ---
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def generate_with_retry(model, prompt):
    return model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.8))

st.subheader("🚀 手動精準推送")
target_id = st.text_input("目標 UserID / 群組 ID", value=DEFAULT_TARGET_ID)

if st.button("執行推送"):
    try:
        api_key = get_secret("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        themes = ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"]
        chosen_theme = random.choice(themes)
        prompt = f"你是溫柔牧者。請針對主題「{chosen_theme}」，精選一段聖經經文。格式：【經文內容】(阿們。)；【章節】；【領受與感悟】。"
        with st.spinner("🚀 牧者正在領受啟示..."):
            res = generate_with_retry(model, prompt)
        if res and res.text:
            payload = res.text.strip()
            send_line_message(target_id.strip(), f'【每日靈修】\n\n{payload}')
            st.success(f"✅ 發送成功")
            history = load_history()
            history.insert(0, {"date": datetime.now(TZ_TW).strftime("%Y-%m-%d"), "time": datetime.now(TZ_TW).strftime("%H:%M:%S"), "category": f"手動-{chosen_theme}", "content": payload})
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"❌ 系統故障: {str(e)}")
```

換成：
```python
st.subheader("🚀 手動精準推送")
target_id = st.text_input("目標 UserID / 群組 ID", value=DEFAULT_TARGET_ID)

if st.button("執行推送"):
    try:
        api_key = get_secret("GEMINI_API_KEY")
        line_token = get_secret("LINE_TOKEN")
        with st.spinner("🚀 牧者正在領受啟示..."):
            payload, chosen_theme = bible_core.generate_verse(api_key, model_name)
        bible_core.send_line_message(line_token, target_id.strip(), f'【每日靈修】\n\n{payload}')
        bible_core.record_entry(payload, f"手動-{chosen_theme}")
        st.success(f"✅ 發送成功")
    except Exception as e:
        st.error(f"❌ 系統故障: {str(e)}")
```

- [ ] **Step 4: 修改「歷史管理」區塊讀取歷史紀錄的地方**

原本：
```python
st.subheader("📚 歷史經文典藏管理庫")
history_data = load_history()
```

換成：
```python
st.subheader("📚 歷史經文典藏管理庫")
history_data = bible_core.load_history()
```

以及原本下載按鈕裡呼叫 `generate_html_backup(...)` 的兩處，改成 `bible_core.generate_html_backup(...)`（呼叫方式與參數完全不變，只是加上 `bible_core.` 前綴）。

- [ ] **Step 5: 手動驗證語法**

Run: `python -m py_compile main.py`
Expected: 沒有任何輸出。

- [ ] **Step 6: Commit**

```bash
git add main.py
git commit -m "refactor: main.py uses bible_core"
```

---

## Task 4: 建立指令解析模組 `command_parser.py`

**Files:**
- Create: `command_parser.py`

**Interfaces:**
- Produces：`command_parser.parse_command(text: str) -> tuple[str | None, object | None]`
  - 回傳值第一項是指令名稱字串，取值範圍：`"push"`、`"theme"`、`"history"`、`"history_error"`、`"download"`、`"menu"`、`"whoami"`、`None`（都不符合時）
  - 第二項是該指令的參數：`"theme"` 時是主題字串；`"history"` 時是正整數；其餘情況是 `None`

- [ ] **Step 1: 寫 `command_parser.py`**

```python
def parse_command(text):
    text = text.strip()

    if text == "推播":
        return ("push", None)

    if text.startswith("主題 "):
        arg = text[len("主題 "):].strip()
        return ("theme", arg) if arg else (None, None)

    if text == "歷史" or text.startswith("歷史 "):
        rest = text[len("歷史"):].strip()
        if rest == "":
            return ("history", 5)
        if rest.isdigit() and int(rest) > 0:
            return ("history", int(rest))
        return ("history_error", None)

    if text == "下載":
        return ("download", None)

    if text == "選單":
        return ("menu", None)

    if text == "我的ID":
        return ("whoami", None)

    return (None, None)
```

- [ ] **Step 2: 手動驗證（純函式，不需要任何環境變數）**

Run:
```bash
python -c "
from command_parser import parse_command
cases = ['推播', '主題 平安', '主題 ', '歷史', '歷史 5', '歷史 abc', '歷史 0', '歷史 -1', '下載', '選單', '我的ID', '靈修一下', '亂打文字']
for c in cases:
    print(repr(c), '->', parse_command(c))
"
```

Expected:
```
'推播' -> ('push', None)
'主題 平安' -> ('theme', '平安')
'主題 ' -> (None, None)
'歷史' -> ('history', 5)
'歷史 5' -> ('history', 5)
'歷史 abc' -> ('history_error', None)
'歷史 0' -> ('history_error', None)
'歷史 -1' -> ('history_error', None)
'下載' -> ('download', None)
'選單' -> ('menu', None)
'我的ID' -> ('whoami', None)
'靈修一下' -> (None, None)
'亂打文字' -> (None, None)
```

- [ ] **Step 3: Commit**

```bash
git add command_parser.py
git commit -m "feat: add command_parser for LINE text commands"
```

---

## Task 5: `app.py` 加上權限機制與 `我的ID` 指令

**Files:**
- Modify: `app.py:1-22`（頂部設定區加 `ADMIN_USER_ID` 與 `is_admin`）

**Interfaces:**
- Consumes：Task 4 的 `command_parser.parse_command`
- Produces：`app.is_admin(event) -> bool`，供 Task 7 使用

- [ ] **Step 1: 修改 `app.py` 頂部設定區**

原本：
```python
from flask import Flask, request, abort
from linebot import WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot import LineBotApi
import os
import google.generativeai as genai
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 初始化設定
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])
line_api = LineBotApi(os.environ['LINE_TOKEN'])
genai.configure(api_key=os.environ['GEMINI_API_KEY'])

# 讀取環境變數中的模型名稱
model_name = os.environ.get('GEMINI_MODEL_NAME', 'models/gemini-flash-latest')
model = genai.GenerativeModel(model_name)
```

換成：
```python
from flask import Flask, request, abort
from linebot import WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    QuickReply, QuickReplyButton, MessageAction,
)
from linebot import LineBotApi
import os
import logging

import bible_core
from command_parser import parse_command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 初始化設定
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])
line_api = LineBotApi(os.environ['LINE_TOKEN'])

# 讀取環境變數中的模型名稱
model_name = os.environ.get('GEMINI_MODEL_NAME', 'models/gemini-flash-latest')

# 有權限使用 推播/主題 指令的 LINE User ID（在 Render 環境變數設定）
ADMIN_USER_ID = os.environ.get('ADMIN_USER_ID', '').strip()


def is_admin(event):
    user_id = getattr(event.source, "user_id", None)
    return bool(ADMIN_USER_ID) and user_id == ADMIN_USER_ID
```

註：原本 `genai.configure(...)` 與 `model = genai.GenerativeModel(...)` 這兩行拿掉，因為生成經文改由 `bible_core.generate_verse(api_key, model_name, ...)` 內部處理（見 Task 1），`app.py` 不需要再自己管理 `genai` 物件。

- [ ] **Step 2: 手動驗證 `is_admin`（用假的環境變數，不需要真的 secrets）**

Run:
```bash
python -c "
import os
os.environ['LINE_CHANNEL_SECRET'] = 'dummy'
os.environ['LINE_TOKEN'] = 'dummy'
os.environ['GEMINI_API_KEY'] = 'dummy'
os.environ['ADMIN_USER_ID'] = 'Uadmin123'
import app

class FakeSource:
    user_id = 'Uadmin123'
class FakeEvent:
    source = FakeSource()

print('admin match:', app.is_admin(FakeEvent()))
FakeSource.user_id = 'Uother456'
print('non-admin:', app.is_admin(FakeEvent()))
"
```

Expected:
```
admin match: True
non-admin: False
```

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add ADMIN_USER_ID permission check to app.py"
```

---

## Task 6: `app.py` 加上 `/export` 路由

**Files:**
- Modify: `app.py`（在 `/callback` 路由後面新增 `/export` 路由）

**Interfaces:**
- Consumes：Task 1 的 `bible_core.load_history`、`bible_core.generate_html_backup`
- Produces：`get_export_url() -> str`，供 Task 7 的「下載」指令使用

- [ ] **Step 1: 在 `@app.route("/callback", ...)` 函式後面加入**

```python
def get_export_url():
    base = os.environ.get('RENDER_EXTERNAL_URL', '').strip()
    if not base:
        base = f"http://localhost:{os.environ.get('PORT', 5000)}"
    return base.rstrip('/') + "/export"


@app.route("/export")
def export_history():
    data = bible_core.load_history()
    return bible_core.generate_html_backup(data)
```

（`RENDER_EXTERNAL_URL` 是 Render 平台會自動注入的環境變數，內容是這個服務對外的公開網址，不需要手動設定；本機執行時沒有這個變數，會退回 `localhost`。）

- [ ] **Step 2: 手動驗證（用 Flask 內建的 test_client，不需要真的啟動伺服器）**

Run:
```bash
python -c "
import os
os.environ['LINE_CHANNEL_SECRET'] = 'dummy'
os.environ['LINE_TOKEN'] = 'dummy'
os.environ['GEMINI_API_KEY'] = 'dummy'
import app

client = app.app.test_client()
resp = client.get('/export')
print('status:', resp.status_code)
print('body starts with:', resp.data[:20])
print('export url (no RENDER_EXTERNAL_URL):', app.get_export_url())

os.environ['RENDER_EXTERNAL_URL'] = 'https://daily-bible-bot.onrender.com'
print('export url (with RENDER_EXTERNAL_URL):', app.get_export_url())
"
```

Expected:
```
status: 200
body starts with: b'<html><head><meta'
export url (no RENDER_EXTERNAL_URL): http://localhost:5000/export
export url (with RENDER_EXTERNAL_URL): https://daily-bible-bot.onrender.com/export
```

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add /export route for history backup download"
```

---

## Task 7: `app.py` 整合完整指令處理邏輯

**Files:**
- Modify: `app.py`（重寫 `handle_message` 函式）

**Interfaces:**
- Consumes：Task 1 的 `bible_core.generate_verse`/`send_line_message`/`record_entry`/`load_history`；Task 4 的 `parse_command`；Task 5 的 `is_admin`；Task 6 的 `get_export_url`

- [ ] **Step 1: 在 `app.py` 裡新增 Quick Reply 產生函式，並整個換掉 `handle_message`**

原本的 `handle_message`：
```python
@handler.add(MessageEvent)
def handle_message(event):
    TARGET_ID = os.environ.get('TARGET_GROUP_ID')
    
    if event.source.type == "group":
        captured_id = event.source.group_id
        with open("latest_group_id.txt", "w") as f:
            f.write(captured_id)
    
    if event.source.type == "group" and event.source.group_id != TARGET_ID:
        return 

    if isinstance(event.message, TextMessage) and "靈修" in event.message.text:
        try:
            res = model.generate_content("請精選一段聖經經文分享。格式：【經文】；【章節】；【感悟】")
            line_api.reply_message(event.reply_token, TextSendMessage(text=res.text))
        except Exception as e:
            logger.error(f"靈修生成失敗: {e}")
            line_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 靈修內容暫時無法讀取。"))
```

換成：
```python
def build_quick_reply(event):
    buttons = [
        QuickReplyButton(action=MessageAction(label="查歷史", text="歷史 5")),
        QuickReplyButton(action=MessageAction(label="下載", text="下載")),
    ]
    if is_admin(event):
        buttons.insert(0, QuickReplyButton(action=MessageAction(label="推播", text="推播")))
    return QuickReply(items=buttons)


@handler.add(MessageEvent)
def handle_message(event):
    TARGET_ID = os.environ.get('TARGET_GROUP_ID')

    if event.source.type == "group":
        captured_id = event.source.group_id
        with open(bible_core.ID_FILE, "w") as f:
            f.write(captured_id)

    if event.source.type == "group" and event.source.group_id != TARGET_ID:
        return

    if not isinstance(event.message, TextMessage):
        return

    text = event.message.text
    command, arg = parse_command(text)

    if command == "whoami":
        line_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"你的 User ID 是：\n{getattr(event.source, 'user_id', '無法取得')}")
        )
        return

    if command == "menu":
        line_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請選擇功能：", quick_reply=build_quick_reply(event))
        )
        return

    if command == "history_error":
        line_api.reply_message(
            event.reply_token,
            TextSendMessage(text="⚠️ 格式錯誤，請用「歷史 5」這種格式（數字需為正整數）")
        )
        return

    if command == "history":
        try:
            items = bible_core.load_history()[:arg]
            if not items:
                reply_text = "目前還沒有歷史紀錄。"
            else:
                reply_text = "\n\n".join(
                    f"{h.get('date')} | {h.get('category')}\n{h.get('content')}" for h in items
                )
            line_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        except Exception as e:
            logger.error(f"查歷史失敗: {e}")
            line_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 暫時無法處理，稍後再試"))
        return

    if command == "download":
        line_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"完整歷史備份：\n{get_export_url()}")
        )
        return

    if command in ("push", "theme"):
        if not is_admin(event):
            line_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 這個指令你沒有權限使用"))
            return
        try:
            theme = arg if command == "theme" else None
            payload, chosen_theme = bible_core.generate_verse(
                os.environ['GEMINI_API_KEY'], model_name, theme=theme
            )
            bible_core.send_line_message(os.environ['LINE_TOKEN'], TARGET_ID, f'【每日靈修】\n\n{payload}')
            bible_core.record_entry(payload, f"指令-{chosen_theme}")
            line_api.reply_message(event.reply_token, TextSendMessage(text="✅ 已推播"))
        except Exception as e:
            logger.error(f"指令推播失敗: {e}")
            line_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 暫時無法處理，稍後再試"))
        return

    if "靈修" in text:
        try:
            payload, _ = bible_core.generate_verse(os.environ['GEMINI_API_KEY'], model_name)
            line_api.reply_message(event.reply_token, TextSendMessage(text=payload))
        except Exception as e:
            logger.error(f"靈修生成失敗: {e}")
            line_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 靈修內容暫時無法讀取。"))
```

- [ ] **Step 2: 手動驗證路由邏輯（用假資料 mock 掉會真的打網路的函式）**

Run:
```bash
python -c "
import os
os.environ['LINE_CHANNEL_SECRET'] = 'dummy'
os.environ['LINE_TOKEN'] = 'dummy'
os.environ['GEMINI_API_KEY'] = 'dummy'
os.environ['TARGET_GROUP_ID'] = 'Cdummygroup'
os.environ['ADMIN_USER_ID'] = 'Uadmin'
import app
import bible_core
from linebot.models import TextMessage
from unittest.mock import patch

class FakeSource:
    type = 'user'
    user_id = 'Uadmin'
class FakeEvent:
    source = FakeSource()
    message = TextMessage(text='推播')
    reply_token = 'dummy-token'

# 情境一：admin 打「推播」，應該真的呼叫 generate_verse/send_line_message
with patch.object(bible_core, 'generate_verse', return_value=('假經文內容', '平安')) as gen, \
     patch.object(bible_core, 'send_line_message') as send, \
     patch.object(app.line_api, 'reply_message') as reply:
    app.handle_message(FakeEvent())
    print('admin push -> generate_verse called:', gen.called)
    print('admin push -> send_line_message called:', send.called)
    print('admin push -> reply text:', reply.call_args[0][1].text)

# 情境二：非 admin 打「推播」，應該被拒絕，不觸發 generate_verse
FakeSource.user_id = 'Uother'
with patch.object(bible_core, 'generate_verse') as gen, \
     patch.object(app.line_api, 'reply_message') as reply:
    app.handle_message(FakeEvent())
    print('non-admin push -> generate_verse called:', gen.called)
    print('non-admin push -> reply text:', reply.call_args[0][1].text)
"
```

Expected:
```
admin push -> generate_verse called: True
admin push -> send_line_message called: True
admin push -> reply text: ✅ 已推播
non-admin push -> generate_verse called: False
non-admin push -> reply text: ⚠️ 這個指令你沒有權限使用
```

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: wire push/theme/history/download/menu commands into handle_message"
```

---

## Task 8: 更新 `CLAUDE.md` 文件

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:** 無（純文件更新）

- [ ] **Step 1: 在「Secrets / 環境變數」的「Render 環境變數」清單加入 `ADMIN_USER_ID`**

在 `CLAUDE.md` 的這段：
```markdown
**Render 環境變數**（供 `app.py` 使用，跟這個 repo 無關，要改去 Render 後台改）：
- `LINE_CHANNEL_SECRET`
- `LINE_TOKEN`
- `GEMINI_API_KEY`
- `TARGET_GROUP_ID`（optional）
```

改成：
```markdown
**Render 環境變數**（供 `app.py` 使用，跟這個 repo 無關，要改去 Render 後台改）：
- `LINE_CHANNEL_SECRET`
- `LINE_TOKEN`
- `GEMINI_API_KEY`
- `TARGET_GROUP_ID`（optional）
- `ADMIN_USER_ID`：Brett 本人的 LINE User ID，用來判斷「推播」「主題」指令的權限。取得方式：在 LINE 裡打「我的ID」，機器人會回覆傳訊者的 User ID。
- `RENDER_EXTERNAL_URL`：Render 平台自動注入，不用手動設定，`app.py` 的 `/export` 路由靠這個組出對外網址。
```

- [ ] **Step 2: 在架構說明的 `app.py` 段落補上指令說明**

在 `CLAUDE.md` 的「### 2. `app.py` — LINE Webhook 被動回覆」段落最後加一句：

```markdown
- 支援文字指令（見 [docs/superpowers/specs/2026-07-22-line-command-console-design.md](docs/superpowers/specs/2026-07-22-line-command-console-design.md)）：`推播`、`主題 <名稱>`（僅 Brett）、`歷史 <N>`、`下載`、`選單`、`我的ID`
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document ADMIN_USER_ID and new LINE commands in CLAUDE.md"
```

---

## Task 9（人工執行，非 subagent）：部署與真人驗證

這個任務需要 Render 後台存取權跟 Brett 自己的 LINE 帳號，subagent 沒有這些權限，必須由 Brett 本人完成。

- [ ] Push 所有 commit 到 GitHub（app.py 有變動時 Render 若有設定 auto-deploy 會自動重新部署；沒設定的話要手動在 Render 觸發 deploy）
- [ ] 在 LINE 裡打「我的ID」，把回傳的 User ID 存進 Render 的 `ADMIN_USER_ID` 環境變數，存完 Render 會自動重啟服務
- [ ] 用 Brett 帳號打「推播」→ 應收到新經文推播到目標群組，且 `bible_history.json` 多一筆紀錄
- [ ] 用另一個帳號（或請群組其他成員）打「推播」→ 應收到「沒有權限」提示，且**沒有**觸發推播
- [ ] 打「主題 平安」→ 生成內容應與「平安」主題相關
- [ ] 打「歷史 3」→ 回傳剛好 3 筆，格式正確
- [ ] 打「歷史 abc」→ 不噴錯，回覆格式提示
- [ ] 打「下載」→ 收到連結，手動點開確認能看到完整歷史
- [ ] 打「選單」→ 收到 Quick Reply 按鈕，Brett 帳號看到「推播」按鈕，其他人不會看到
- [ ] 確認 GitHub Actions 排程（`daily_push.py`）跟本機 `main.py` 控制台都還能正常運作（各手動觸發一次驗證）
