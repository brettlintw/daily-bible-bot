# 經文防重複機制 + 新增主題 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `generate_verse` 的防重複機制從「拜託 Gemini 自己避開」改成「生成後程式驗證、撞到就重打，最多 3 次」，保證區間拉長到 5 個月，並新增 5 個經文主題。

**Architecture:** `bible_core.py` 新增 `extract_reference`（從內容抓經文章節識別碼）與 `get_recent_references`（讀歷史、篩 5 個月內、抓識別碼集合）兩個工具函式；把 `generate_verse` 原本「生成一次就回傳」的邏輯抽成內部函式 `_generate_once`，外層包一個「生成→驗證→必要時重打，最多 3 次」的迴圈。三個進入點（`daily_push.py`／`app.py`／`main.py`）都呼叫同一個 `generate_verse`，不需要個別修改。

**Tech Stack:** Python 標準函式庫 `re`（新用，判斷經文章節），其餘沿用既有的 `google-generativeai`、`tenacity`。不新增套件。

## Global Constraints

- 個人小專案，不引入 pytest 或任何自動化測試框架；驗證一律用 `unittest.mock` 模擬，不觸發真實網路呼叫
- `generate_verse` 對外簽章維持 `(api_key, model_name=None, theme=...)` 可呼叫、回傳值維持 `(經文內容字串, 實際使用的主題字串)` 的 tuple，三個既有呼叫端（`daily_push.py`、`app.py` 兩處、`main.py`）都不需要修改呼叫方式
- 既有的多模型容錯邏輯（`model_name=None` 時依序嘗試 `FREE_MODEL_CANDIDATES`，指定時走 `_generate_with_retry`）維持不變，只是被包進新的重打迴圈裡
- 重打邏輯：`theme` 有指定值時，重打維持同一主題；`theme=None`（自動情境）時，每次重打重新隨機選主題
- 重打 3 次都還是重複的話，直接採用第 3 次結果照常回傳，不拋例外、不中斷
- 所有使用者可見文字、log 訊息維持繁體中文

---

## Task 1: `bible_core.py` — 新增經文識別碼工具函式

**Files:**
- Modify: `bible_core.py:1-17`（新增 `import re`）
- Modify: `bible_core.py`（新增兩個函式，緊接在 `THEMES`/`FREE_MODEL_CANDIDATES` 常數之後、`load_history` 之前）

**Interfaces:**
- Produces：
  - `bible_core.extract_reference(content: str) -> str | None`：從內容裡抓出「《書卷》...節」這段文字，抓不到回傳 `None`
  - `bible_core.get_recent_references(months: int = 5, db_file: str = DB_FILE) -> set[str]`：回傳最近 N 個月內、所有能抓出識別碼的紀錄組成的集合

- [ ] **Step 1: 在檔案開頭加入 `import re`**

原本（`bible_core.py:1-10`）：
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
```

換成：
```python
import os
import re
import json
import random
import logging
from datetime import datetime, timezone, timedelta

import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage
from tenacity import retry, stop_after_attempt, wait_exponential
```

- [ ] **Step 2: 在 `FREE_MODEL_CANDIDATES` 常數後面（`load_history` 定義前）新增兩個函式**

在這段（`bible_core.py:19-24`）：
```python
FREE_MODEL_CANDIDATES = [
    ("models/gemini-2.5-flash-lite", "成本最低，優先使用"),
    ("models/gemini-flash-latest", "成本次低"),
    ("models/gemini-2.5-flash", "成本較高，當保底"),
]
```

後面插入：
```python
REFERENCE_PATTERN = re.compile(r'《[^》]+》[^；\n]*')


def extract_reference(content):
    match = REFERENCE_PATTERN.search(content)
    if match:
        return match.group(0).strip()
    return None


def get_recent_references(months=5, db_file=DB_FILE):
    cutoff = datetime.now(TZ_TW) - timedelta(days=30 * months)
    cutoff_date_str = cutoff.strftime("%Y-%m-%d")
    refs = set()
    for entry in load_history(db_file):
        if entry.get("date", "") >= cutoff_date_str:
            ref = extract_reference(entry.get("content", ""))
            if ref:
                refs.add(ref)
    return refs
```

（`get_recent_references` 呼叫了 `load_history`，這個函式在檔案裡定義的位置在它後面沒關係——Python 是等到函式真的被呼叫時才去找 `load_history`，不是定義的當下就要找到，所以順序不影響執行。）

- [ ] **Step 3: 手動驗證**

Run:
```bash
python -c "
import bible_core

# 情境一：有【章節】標籤的正常格式
c1 = '【內容】因為，耶和華賜人智慧。；【章節】《箴言》第二章6節；【領受】親愛的弟兄姊妹...'
print('情境一:', bible_core.extract_reference(c1))

# 情境二：沒有【章節】標籤（實際觀察到 Gemini 有時會漏寫)
c2 = '【內容】...盼望不至於羞恥。」；《羅馬書》第五章3-5節；【領受】親愛的弟兄姊妹...'
print('情境二:', bible_core.extract_reference(c2))

# 情境三：完全抓不到書卷格式
c3 = '這是一段沒有書卷章節格式的亂碼內容'
print('情境三:', bible_core.extract_reference(c3))
"
```

Expected:
```
情境一: 《箴言》第二章6節
情境二: 《羅馬書》第五章3-5節
情境三: None
```

Run（驗證 `get_recent_references` 的日期篩選邏輯，用暫存檔案不動到真正的 `bible_history.json`）：
```bash
python -c "
import json, tempfile, os
from datetime import datetime, timezone, timedelta
import bible_core

TZ_TW = timezone(timedelta(hours=8))
today = datetime.now(TZ_TW)
recent_date = (today - timedelta(days=10)).strftime('%Y-%m-%d')
old_date = (today - timedelta(days=200)).strftime('%Y-%m-%d')

fake_data = [
    {'date': recent_date, 'time': '10:00:00', 'category': '測試', 'content': '【內容】A；【章節】《箴言》第二章6節；【領受】...'},
    {'date': old_date, 'time': '10:00:00', 'category': '測試', 'content': '【內容】B；【章節】《羅馬書》第八章37節；【領受】...'},
]

fd, path = tempfile.mkstemp(suffix='.json')
os.close(fd)
with open(path, 'w', encoding='utf-8') as f:
    json.dump(fake_data, f, ensure_ascii=False)

refs = bible_core.get_recent_references(months=5, db_file=path)
print('refs:', refs)
os.remove(path)
"
```

Expected:
```
refs: {'《箴言》第二章6節'}
```
（200 天前的《羅馬書》那筆超過 5 個月，`{'《箴言》第二章6節'}` 是唯一結果——順序不影響，因為是集合。）

- [ ] **Step 4: 手動驗證語法**

Run: `python -m py_compile bible_core.py`
Expected: 沒有任何輸出。

- [ ] **Step 5: Commit**

```bash
git add bible_core.py
git commit -m "feat: add extract_reference and get_recent_references helpers"
```

---

## Task 2: `bible_core.py` — 重寫 `generate_verse` 加入防重複重打迴圈，新增 5 個主題

**Files:**
- Modify: `bible_core.py:17`（`THEMES` 常數）
- Modify: `bible_core.py`（原本的 `generate_verse` 函式整個重寫）

**Interfaces:**
- Consumes：Task 1 的 `bible_core.extract_reference`、`bible_core.get_recent_references`
- Produces：
  - `bible_core._generate_once(api_key, model_name, chosen_theme, avoid_refs) -> str`（內部函式，回傳生成的原始內容字串，不含主題資訊）
  - `bible_core.generate_verse(api_key, model_name=None, theme=None, dedup_months=5, max_attempts=3) -> tuple[str, str]`（對外簽章相容既有呼叫端；新增兩個有預設值的參數，不影響既有呼叫）

- [ ] **Step 1: 更新 `THEMES`**

原本（`bible_core.py:17`）：
```python
THEMES = ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"]
```

換成：
```python
THEMES = ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心", "感恩", "喜樂", "忍耐", "謙卑", "引導"]
```

- [ ] **Step 2: 重寫 `generate_verse`**

原本：
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

換成：
```python
def _generate_once(api_key, model_name, chosen_theme, avoid_refs):
    genai.configure(api_key=api_key)

    avoid_str = "\n".join(sorted(avoid_refs)) if avoid_refs else "（無）"

    prompt = f"""
    你是一位充滿智慧的資深牧者。
    請精選一段聖經經文。
    主題選擇：{chosen_theme}。

    【絕對禁令】：嚴禁輸出與下方清單相同的經文章節。
    這是一份最近 5 個月已經分享過的經文章節清單 (請避開以下所有章節)：
    {avoid_str}

    請依照此格式嚴格輸出：
    【內容】；【章節】；【領受】。
    """

    if model_name:
        model = genai.GenerativeModel(model_name)
        res = _generate_with_retry(model, prompt)
        return res.text.strip()

    last_error = None
    for candidate_name, _label in FREE_MODEL_CANDIDATES:
        try:
            model = genai.GenerativeModel(candidate_name)
            res = model.generate_content(
                prompt, generation_config=genai.types.GenerationConfig(temperature=0.8)
            )
            return res.text.strip()
        except Exception as e:
            logger.error(f"模型 {candidate_name} 失敗：{e}，改試下一個")
            last_error = e
    raise last_error


def generate_verse(api_key, model_name=None, theme=None, dedup_months=5, max_attempts=3):
    avoid_refs = get_recent_references(months=dedup_months)

    last_payload, last_theme = None, None
    for attempt in range(1, max_attempts + 1):
        chosen_theme = theme or random.choice(THEMES)
        payload = _generate_once(api_key, model_name, chosen_theme, avoid_refs)
        ref = extract_reference(payload)
        last_payload, last_theme = payload, chosen_theme

        if ref is None or ref not in avoid_refs:
            return payload, chosen_theme

        logger.error(f"第 {attempt} 次生成撞到重複經文（{ref}），重打")

    logger.error(f"重試 {max_attempts} 次仍重複，直接採用最後一次結果")
    return last_payload, last_theme
```

- [ ] **Step 3: 手動驗證（mock 掉 `_generate_once`，不需要真實 API Key、不觸發真實網路）**

Run:
```bash
python -c "
import bible_core
from unittest.mock import patch

fake_avoid = {'《箴言》第二章6節'}

# 情境一：前兩次都撞到重複，第三次才換一節 -> 應該回傳第三次的結果
responses = [
    '【內容】重複內容A；【章節】《箴言》第二章6節；【領受】...',
    '【內容】重複內容A；【章節】《箴言》第二章6節；【領受】...',
    '【內容】新內容B；【章節】《詩篇》第一篇3節；【領受】...',
]
with patch.object(bible_core, 'get_recent_references', return_value=fake_avoid), \
     patch.object(bible_core, '_generate_once', side_effect=responses) as gen:
    payload, theme = bible_core.generate_verse('dummy-key', theme='盼望')
    print('情境一 payload:', payload)
    print('情境一 呼叫次數:', gen.call_count)
    print('情境一 每次呼叫的主題參數:', [c.args[2] for c in gen.call_args_list])

# 情境二：指定主題時，重打仍固定用同一個主題（驗證上面那行印出的主題參數應該三次都是 '盼望'）

# 情境三：3 次都重複 -> 仍要回傳結果，不拋例外
responses_all_dup = [
    '【內容】A；【章節】《箴言》第二章6節；【領受】...',
    '【內容】A；【章節】《箴言》第二章6節；【領受】...',
    '【內容】A；【章節】《箴言》第二章6節；【領受】...',
]
with patch.object(bible_core, 'get_recent_references', return_value=fake_avoid), \
     patch.object(bible_core, '_generate_once', side_effect=responses_all_dup) as gen:
    payload, theme = bible_core.generate_verse('dummy-key', theme='盼望')
    print('情境三 payload（3 次都重複，仍要有結果）:', payload)
    print('情境三 呼叫次數:', gen.call_count)

# 情境四：theme=None 時，每次重打應該重新隨機選主題（不強制一定要不一樣，但要確認參數真的有在變動邏輯裡被重新計算）
responses_random = [
    '【內容】A；【章節】《箴言》第二章6節；【領受】...',
    '【內容】新內容；【章節】《詩篇》第一篇3節；【領受】...',
]
with patch.object(bible_core, 'get_recent_references', return_value=fake_avoid), \
     patch.object(bible_core, '_generate_once', side_effect=responses_random) as gen, \
     patch('bible_core.random.choice', return_value='喜樂') as choice_mock:
    payload, theme = bible_core.generate_verse('dummy-key')
    print('情境四 payload:', payload)
    print('情境四 theme:', theme)
    print('情境四 random.choice 呼叫次數（應等於實際嘗試次數 2）:', choice_mock.call_count)
"
```

Expected:
```
情境一 payload: 【內容】新內容B；【章節】《詩篇》第一篇3節；【領受】...
情境一 呼叫次數: 3
情境一 每次呼叫的主題參數: ['盼望', '盼望', '盼望']
情境三 payload（3 次都重複，仍要有結果）: 【內容】A；【章節】《箴言》第二章6節；【領受】...
情境三 呼叫次數: 3
情境四 payload: 【內容】新內容；【章節】《詩篇》第一篇3節；【領受】...
情境四 theme: 喜樂
情境四 random.choice 呼叫次數（應等於實際嘗試次數 2）: 2
```

- [ ] **Step 4: 手動驗證語法**

Run: `python -m py_compile bible_core.py`
Expected: 沒有任何輸出。

- [ ] **Step 5: Commit**

```bash
git add bible_core.py
git commit -m "feat: verify-and-retry duplicate verses, add 5 new themes"
```

---

## Task 3: 更新 `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:** 無（純文件更新）

- [ ] **Step 1: 在「Gemini 模型自動容錯」段落後面新增一段說明**

在 `CLAUDE.md` 的「## Gemini 模型自動容錯」整節之後（也就是「## requirements.txt 備註」這個標題之前），插入：

```markdown
## 經文防重複機制

`generate_verse` 會在生成經文後，用 `extract_reference` 抓出「《書卷》第X章Y節」這段當作識別碼，跟 `get_recent_references(months=5)` 算出的「最近 5 個月已經推過的章節」比對。撞到就重打，最多重打 3 次；3 次都撞到的話，直接採用第 3 次的結果照常推播（不會因此中斷推播），並記一行 log。

背景：2026-09 發現同一節經文常常一個月內重複好幾次（例如雅各書 1:5 一個月出現 3 次），原因是舊機制只在 prompt 裡「拜託」Gemini 避開最近 30 筆內容，沒有程式層級驗證。這次改成生成後實際驗證，不再只靠 AI 自覺遵守指示。

`THEMES` 目前有 12 個主題（原本 7 個 + 感恩、喜樂、忍耐、謙卑、引導）。
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document verse dedup mechanism and expanded theme list"
```

## Self-Review Notes

**Spec coverage：** 經文識別碼抓取（含無標籤格式）✅（Task 1），5 個月時間窗口比對 ✅（Task 1 `get_recent_references`），生成→驗證→重打最多 3 次 ✅（Task 2），指定主題時重打維持同主題／自動情境每次重新隨機 ✅（Task 2，`theme or random.choice(THEMES)` 每次迭代都重新求值），3 次都重複仍正常推播不中斷 ✅（Task 2 迴圈跑完直接 return last_payload），prompt 內容從 60 字片段改成章節清單 ✅（Task 2 `_generate_once` 的 `avoid_str`），新增 5 個主題 ✅（Task 2 Step 1），三個進入點不需修改 ✅（`generate_verse` 對外簽章相容，未變更任何呼叫端），CLAUDE.md 記錄 ✅（Task 3）。

**Type consistency：** `generate_verse` 回傳值全程維持 `(str, str)` tuple，跟 `daily_push.py`/`app.py`/`main.py` 既有的 `payload, chosen_theme = bible_core.generate_verse(...)` 解構寫法一致，未變更。`_generate_once` 是新的內部函式，只在 `generate_verse` 內部呼叫，不影響任何外部呼叫端。`extract_reference`/`get_recent_references` 的函式名稱、參數在 Task 1 定義、Task 2 呼叫端都一致（`get_recent_references(months=dedup_months)`、`extract_reference(payload)`）。
