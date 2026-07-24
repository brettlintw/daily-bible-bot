# Gemini 模型自動容錯 + 手動選擇 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓 `bible_core.generate_verse` 在沒有指定模型時，自動依序嘗試多個免費 Gemini 模型（一個撞額度就換下一個），並在 `main.py` 提供下拉選單手動強制指定單一模型。

**Architecture:** `bible_core.py` 新增 `FREE_MODEL_CANDIDATES` 常數，`generate_verse` 依 `model_name` 是否為 `None` 分兩條路徑：`None` 走候選清單依序嘗試（無內建重試，失敗就換下一個），有指定字串走原本單一模型 + tenacity 重試。`daily_push.py`、`app.py` 改成一律用自動模式；`main.py` 新增下拉選單，可選「自動」或強制指定候選清單裡的某一個模型。

**Tech Stack:** Python、`google-generativeai`、`tenacity`（沿用既有）。不新增套件。

## Global Constraints

- 個人小專案，不引入 pytest 或任何自動化測試框架；驗證一律用手動 `python -c` 指令 + `unittest.mock` 模擬 Gemini API 失敗，不觸發真實網路呼叫、不需要真實 API Key
- 自動模式（`model_name=None`）**不**對單一候選模型做 tenacity 重試——任何例外就記 log、換下一個候選；手動指定模式（`model_name="具體字串"`）維持原本的 `_generate_with_retry`（3 次重試）
- `daily_push.py`、`app.py` 都改為呼叫 `bible_core.generate_verse` 時不傳 `model_name`（等同 `None`），`GEMINI_MODEL_NAME` 環境變數之後在這兩個檔案裡不再被讀取（已與 Brett 確認）
- `main.py` 的下拉選單選項要從 `bible_core.FREE_MODEL_CANDIDATES` 動態產生，不手動重複維護一份清單
- 所有使用者可見文字維持繁體中文，語氣與既有程式碼一致

---

## Task 1: `bible_core.py` — 新增候選模型清單與自動容錯邏輯

**Files:**
- Modify: `bible_core.py:17` (新增常數), `bible_core.py:54-76` (`generate_verse` 整個函式)

**Interfaces:**
- Produces：
  - `bible_core.FREE_MODEL_CANDIDATES: list[tuple[str, str]]`（`(模型名稱, 說明標籤)`，依嘗試優先順序排列）
  - `bible_core.generate_verse(api_key: str, model_name: str | None = None, theme: str | None = None, history_limit: int = 30) -> tuple[str, str]`（`model_name` 現在預設 `None`，語意變成「自動模式」；行為對外回傳值不變，仍是 `(經文內容, 實際使用的主題)`）

- [ ] **Step 1: 在 `THEMES` 常數後面加入 `FREE_MODEL_CANDIDATES`**

在 `bible_core.py` 第 17 行（`THEMES = [...]`）後面插入：

```python
FREE_MODEL_CANDIDATES = [
    ("models/gemini-2.5-flash-lite", "額度通常較寬鬆"),
    ("models/gemini-2.0-flash-lite", "額度通常較寬鬆"),
    ("models/gemini-2.5-flash", "額度普通"),
    ("models/gemini-flash-latest", "目前預設，額度較容易撞牆"),
]
```

- [ ] **Step 2: 重寫 `generate_verse`**

原本（`bible_core.py:54-76`）：
```python
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
```

換成：
```python
def generate_verse(api_key, model_name=None, theme=None, history_limit=30):
    genai.configure(api_key=api_key)

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

    if model_name:
        model = genai.GenerativeModel(model_name)
        res = _generate_with_retry(model, prompt)
        return res.text.strip(), chosen_theme

    last_error = None
    for candidate_name, _label in FREE_MODEL_CANDIDATES:
        try:
            model = genai.GenerativeModel(candidate_name)
            res = model.generate_content(
                prompt, generation_config=genai.types.GenerationConfig(temperature=0.8)
            )
            return res.text.strip(), chosen_theme
        except Exception as e:
            logger.error(f"模型 {candidate_name} 失敗：{e}，改試下一個")
            last_error = e
    raise last_error
```

- [ ] **Step 3: 手動驗證（mock 掉 Gemini 呼叫，不需要真實 API Key、不觸發真實網路）**

Run:
```bash
python -c "
import bible_core
from unittest.mock import patch, MagicMock

calls = []

def fake_generative_model(name):
    calls.append(name)
    m = MagicMock()
    if name in ('models/gemini-2.5-flash-lite', 'models/gemini-2.0-flash-lite'):
        m.generate_content.side_effect = Exception('quota exceeded (fake)')
    else:
        m.generate_content.return_value = MagicMock(text='假經文內容')
    return m

# 情境一：前兩個候選失敗，第三個成功
with patch('bible_core.genai.configure'), patch('bible_core.genai.GenerativeModel', side_effect=fake_generative_model):
    payload, theme = bible_core.generate_verse('dummy-key', None, theme='平安')
    print('情境一 payload:', payload)
    print('情境一 theme:', theme)
    print('情境一 嘗試順序:', calls)

# 情境二：全部候選都失敗，應該把最後一個例外往外拋
calls.clear()
def always_fail(name):
    calls.append(name)
    m = MagicMock()
    m.generate_content.side_effect = Exception(f'quota exceeded on {name}')
    return m

with patch('bible_core.genai.configure'), patch('bible_core.genai.GenerativeModel', side_effect=always_fail):
    try:
        bible_core.generate_verse('dummy-key', None)
        print('情境二: 不應該執行到這裡')
    except Exception as e:
        print('情境二 raised:', e)
        print('情境二 嘗試過的候選數:', len(calls))

# 情境三：手動指定模型時，只會呼叫那一個，不會跑候選清單
calls.clear()
def single_ok(name):
    calls.append(name)
    m = MagicMock()
    m.generate_content.return_value = MagicMock(text='指定模型的經文')
    return m

with patch('bible_core.genai.configure'), patch('bible_core.genai.GenerativeModel', side_effect=single_ok):
    payload, theme = bible_core.generate_verse('dummy-key', 'models/gemini-2.5-flash', theme='信心')
    print('情境三 payload:', payload)
    print('情境三 呼叫過的模型:', calls)
"
```

Expected:
```
情境一 payload: 假經文內容
情境一 theme: 平安
情境一 嘗試順序: ['models/gemini-2.5-flash-lite', 'models/gemini-2.0-flash-lite', 'models/gemini-2.5-flash']
情境二 raised: quota exceeded on models/gemini-flash-latest
情境二 嘗試過的候選數: 4
情境三 payload: 指定模型的經文
情境三 呼叫過的模型: ['models/gemini-2.5-flash']
```

- [ ] **Step 4: Commit**

```bash
git add bible_core.py
git commit -m "feat: add free-model fallback list to generate_verse"
```

---

## Task 2: `daily_push.py` — 改用自動模式

**Files:**
- Modify: `daily_push.py:9-13, 22`

**Interfaces:**
- Consumes：Task 1 的 `bible_core.generate_verse(api_key, model_name=None, theme=None, history_limit=30)`

- [ ] **Step 1: 移除 `model_name` 讀取、改用自動模式呼叫**

原本：
```python
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
```

換成：
```python
def main():
    target_id = os.environ.get('TARGET_GROUP_ID', '').strip()
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    line_token = os.environ.get('LINE_TOKEN', '').strip()

    if not all([target_id, api_key, line_token]):
        return

    with open(bible_core.ID_FILE, "w") as f:
        f.write(target_id)

    try:
        payload, chosen_theme = bible_core.generate_verse(api_key)
```

（其餘行數不變：`bible_core.send_line_message(...)`、`bible_core.record_entry(...)`、`except Exception as e:` 都維持原樣。）

- [ ] **Step 2: 手動驗證語法**

Run: `python -m py_compile daily_push.py`
Expected: 沒有任何輸出。

- [ ] **Step 3: Commit**

```bash
git add daily_push.py
git commit -m "refactor: daily_push.py uses generate_verse auto model fallback"
```

---

## Task 3: `app.py` — 改用自動模式

**Files:**
- Modify: `app.py:24-25` (刪除), `app.py:135-137`, `app.py:148`

**Interfaces:**
- Consumes：Task 1 的 `bible_core.generate_verse(api_key, model_name=None, theme=None, history_limit=30)`

- [ ] **Step 1: 刪除 `model_name` 讀取行**

原本（`app.py:24-25`）：
```python
# 讀取環境變數中的模型名稱
model_name = os.environ.get('GEMINI_MODEL_NAME', 'models/gemini-flash-latest')

# 有權限使用 推播/主題 指令的 LINE User ID（在 Render 環境變數設定）
```

換成：
```python
# 有權限使用 推播/主題 指令的 LINE User ID（在 Render 環境變數設定）
```

- [ ] **Step 2: 修改「推播/主題」指令的呼叫**

原本（`app.py:133-137`）：
```python
        try:
            theme = arg if command == "theme" else None
            payload, chosen_theme = bible_core.generate_verse(
                os.environ['GEMINI_API_KEY'], model_name, theme=theme
            )
```

換成：
```python
        try:
            theme = arg if command == "theme" else None
            payload, chosen_theme = bible_core.generate_verse(
                os.environ['GEMINI_API_KEY'], theme=theme
            )
```

- [ ] **Step 3: 修改「靈修」關鍵字回覆的呼叫**

原本（`app.py:148`）：
```python
            payload, _ = bible_core.generate_verse(os.environ['GEMINI_API_KEY'], model_name)
```

換成：
```python
            payload, _ = bible_core.generate_verse(os.environ['GEMINI_API_KEY'])
```

- [ ] **Step 4: 手動驗證（dummy 環境變數，確認 import 跟指令路由不會因為拿掉 `model_name` 而炸掉）**

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

with patch.object(bible_core, 'generate_verse', return_value=('假經文內容', '平安')) as gen, \
     patch.object(bible_core, 'send_line_message') as send, \
     patch.object(app.line_api, 'reply_message') as reply:
    app.handle_message(FakeEvent())
    print('generate_verse 呼叫參數:', gen.call_args)
    print('reply text:', reply.call_args[0][1].text)
"
```

Expected:
```
generate_verse 呼叫參數: call('dummy', theme=None)
reply text: ✅ 已推播
```

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "refactor: app.py uses generate_verse auto model fallback"
```

---

## Task 4: `main.py` — 新增模型選擇下拉選單

**Files:**
- Modify: `main.py:25`, `main.py:27-35`

**Interfaces:**
- Consumes：Task 1 的 `bible_core.FREE_MODEL_CANDIDATES`、`bible_core.generate_verse(api_key, model_name=None, theme=None, ...)`

- [ ] **Step 1: 刪除舊的 `model_name` 讀取行，改用下拉選單**

原本（`main.py:25`）：
```python
model_name = get_secret("GEMINI_MODEL_NAME") or "models/gemini-flash-latest"
```

換成：
```python
MODEL_OPTIONS = {"自動（依序嘗試免費模型，推薦）": None}
MODEL_OPTIONS.update({f"{name}（{label}）": name for name, label in bible_core.FREE_MODEL_CANDIDATES})
```

- [ ] **Step 2: 在「手動精準推送」按鈕上方加入選單，並修改按鈕呼叫**

原本（`main.py:27-35`）：
```python
st.subheader("🚀 手動精準推送")
target_id = st.text_input("目標 UserID / 群組 ID", value=DEFAULT_TARGET_ID)

if st.button("執行推送"):
    try:
        api_key = get_secret("GEMINI_API_KEY")
        line_token = get_secret("LINE_TOKEN")
        with st.spinner("🚀 牧者正在領受啟示..."):
            payload, chosen_theme = bible_core.generate_verse(api_key, model_name)
```

換成：
```python
st.subheader("🚀 手動精準推送")
target_id = st.text_input("目標 UserID / 群組 ID", value=DEFAULT_TARGET_ID)
selected_label = st.selectbox("選擇生成模型：", list(MODEL_OPTIONS.keys()))
selected_model_name = MODEL_OPTIONS[selected_label]

if st.button("執行推送"):
    try:
        api_key = get_secret("GEMINI_API_KEY")
        line_token = get_secret("LINE_TOKEN")
        with st.spinner("🚀 牧者正在領受啟示..."):
            payload, chosen_theme = bible_core.generate_verse(api_key, selected_model_name)
```

（後面 `bible_core.send_line_message(...)`、`bible_core.record_entry(...)`、`st.success(...)`、`except Exception as e: st.error(...)` 都維持原樣不動。）

- [ ] **Step 3: 手動驗證語法**

Run: `python -m py_compile main.py`
Expected: 沒有任何輸出。

- [ ] **Step 4: 手動驗證選單邏輯（不需要啟動 Streamlit，直接檢查 `MODEL_OPTIONS` 這個 dict 組出來對不對）**

Run:
```bash
python -c "
import bible_core
MODEL_OPTIONS = {'自動（依序嘗試免費模型，推薦）': None}
MODEL_OPTIONS.update({f'{name}（{label}）': name for name, label in bible_core.FREE_MODEL_CANDIDATES})
for label, value in MODEL_OPTIONS.items():
    print(repr(label), '->', value)
"
```

Expected（值要跟 `bible_core.FREE_MODEL_CANDIDATES` 的四個候選一一對應，第一項是自動、value 是 `None`）：
```
'自動（依序嘗試免費模型，推薦）' -> None
'models/gemini-2.5-flash-lite（額度通常較寬鬆）' -> models/gemini-2.5-flash-lite
'models/gemini-2.0-flash-lite（額度通常較寬鬆）' -> models/gemini-2.0-flash-lite
'models/gemini-2.5-flash（額度普通）' -> models/gemini-2.5-flash
'models/gemini-flash-latest（目前預設，額度較容易撞牆）' -> models/gemini-flash-latest
```

- [ ] **Step 5: Commit**

```bash
git add main.py
git commit -m "feat: add model selector dropdown to main.py console"
```

---

## Task 5: 更新 `CLAUDE.md`，註記候選清單可能需要跟著 Google 政策調整

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:** 無（純文件更新）

- [ ] **Step 1: 在「requirements.txt 備註」前面加一段新的小節**

在 `CLAUDE.md` 的「## requirements.txt 備註」這行**之前**插入：

```markdown
## Gemini 模型自動容錯

`bible_core.py` 的 `FREE_MODEL_CANDIDATES` 是一份手動維護的免費模型優先順序清單，`generate_verse` 在沒有指定模型時會依序嘗試，一個撞到額度限制就換下一個。Google 常調整免費方案的額度規則，如果之後常常整批失敗（Render log 出現多行「模型 X 失敗」），要去 Google AI Studio 確認現在的免費額度規則，更新這份清單的內容或順序。`GEMINI_MODEL_NAME` 環境變數已經沒有作用了（Render／GitHub Actions 上如果還留著可以不用管，但不會被讀取）。

```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document Gemini model fallback list in CLAUDE.md"
```

---

## Self-Review Notes

**Spec coverage:** FREE_MODEL_CANDIDATES ✅ (Task 1), 自動模式無重試/手動模式保留重試 ✅ (Task 1), daily_push.py/app.py 改自動模式 ✅ (Task 2/3), GEMINI_MODEL_NAME 停用 ✅ (Task 2/3 移除讀取), main.py 下拉選單動態產生 ✅ (Task 4), 每個候選失敗記 log ✅ (Task 1 內建), 手動驗證不打真實 API ✅ (全部 Task 用 mock)。

**Type consistency:** `generate_verse` 簽章 `(api_key, model_name=None, theme=None, history_limit=30)` 在 Task 1 定義、Task 2/3/4 呼叫端都對齊（Task 2/3 省略 `model_name`、`theme` 用預設值或明確傳 `theme=...`；Task 4 明確傳 `selected_model_name`）。`FREE_MODEL_CANDIDATES` 的 `(name, label)` tuple 結構在 Task 1 定義、Task 4 解構使用都一致。
