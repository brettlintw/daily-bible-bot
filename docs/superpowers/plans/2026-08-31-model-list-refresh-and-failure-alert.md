# 模型清單修正 + 全失敗通知 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 移除已下架的 Gemini 模型、把候選清單改成依單價排序，並在 `daily_push.py` 全部候選模型都失敗時主動推 LINE 訊息通知 Brett，避免像 2026-08-31 那次連續多天失敗都沒人發現。

**Architecture:** `bible_core.py` 的 `FREE_MODEL_CANDIDATES` 常數內容更新（拿掉下架的模型、重新排序），`generate_verse` 的邏輯本身不變。`daily_push.py` 讀取新的 `ADMIN_USER_ID` 環境變數，在既有的最外層 `except` 區塊裡，失敗時額外呼叫 `bible_core.send_line_message` 推送給管理員，包在自己的 `try/except` 裡避免二次爆炸。

**Tech Stack:** Python、`google-generativeai`、既有的 `bible_core.send_line_message`。不新增套件、不新增檔案。

## Global Constraints

- 個人小專案，不引入 pytest 或任何自動化測試框架；驗證一律用 `unittest.mock` 模擬失敗情境，不觸發真實網路呼叫
- `FREE_MODEL_CANDIDATES` 只調整內容/順序，`generate_verse` 的自動模式迴圈邏輯（依序嘗試、任何例外換下一個、不重試同一個候選、全部失敗拋出最後一個例外）維持不變，不重寫
- `app.py`（LINE 指令 `推播`）失敗時**不**新增通知邏輯——維持現況，使用者在對話裡本來就會看到即時錯誤訊息
- 通知失敗（LINE API 本身也掛掉）不能讓整個 `daily_push.py` 的既有錯誤處理邏輯中斷或重複拋出例外
- 所有使用者可見文字（LINE 通知內容）維持繁體中文，沿用既有 `⚠️` 等 emoji 風格

---

## Task 1: `bible_core.py` — 更新候選模型清單，順手修正 `main.py` 選單文字

**Files:**
- Modify: `bible_core.py:19-24`
- Modify: `main.py:25`

**Interfaces:**
- Produces：`bible_core.FREE_MODEL_CANDIDATES`（結構不變，仍是 `list[tuple[str, str]]`，僅內容/順序改變）——`generate_verse` 的自動模式邏輯、`main.py` 的 `MODEL_OPTIONS.update(...)` 動態組合邏輯都照舊讀取這個常數，不需要改動

- [ ] **Step 1: 更新 `FREE_MODEL_CANDIDATES`**

原本：
```python
FREE_MODEL_CANDIDATES = [
    ("models/gemini-2.5-flash-lite", "額度通常較寬鬆"),
    ("models/gemini-2.0-flash-lite", "額度通常較寬鬆"),
    ("models/gemini-2.5-flash", "額度普通"),
    ("models/gemini-flash-latest", "目前預設，額度較容易撞牆"),
]
```

換成：
```python
FREE_MODEL_CANDIDATES = [
    ("models/gemini-2.5-flash-lite", "成本最低，優先使用"),
    ("models/gemini-flash-latest", "成本次低"),
    ("models/gemini-2.5-flash", "成本較高，當保底"),
]
```

- [ ] **Step 2: 手動驗證（mock 掉 Gemini 呼叫，確認新清單的三個候選會依序被嘗試）**

Run:
```bash
python -c "
import bible_core
from unittest.mock import patch, MagicMock

print('候選清單:', bible_core.FREE_MODEL_CANDIDATES)
assert len(bible_core.FREE_MODEL_CANDIDATES) == 3, '應該剩 3 個候選'
assert bible_core.FREE_MODEL_CANDIDATES[0][0] == 'models/gemini-2.5-flash-lite'
assert bible_core.FREE_MODEL_CANDIDATES[1][0] == 'models/gemini-flash-latest'
assert bible_core.FREE_MODEL_CANDIDATES[2][0] == 'models/gemini-2.5-flash'
assert not any('2.0-flash-lite' in name for name, _ in bible_core.FREE_MODEL_CANDIDATES), '下架的模型應該已經移除'
print('清單內容/順序正確')

calls = []
def fake_generative_model(name):
    calls.append(name)
    m = MagicMock()
    if name == 'models/gemini-2.5-flash-lite':
        m.generate_content.side_effect = Exception('quota exceeded (fake)')
    else:
        m.generate_content.return_value = MagicMock(text='假經文內容')
    return m

with patch('bible_core.genai.configure'), patch('bible_core.genai.GenerativeModel', side_effect=fake_generative_model):
    payload, theme = bible_core.generate_verse('dummy-key', None, theme='平安')
    print('payload:', payload)
    print('嘗試順序:', calls)
"
```

Expected:
```
候選清單: [('models/gemini-2.5-flash-lite', '成本最低，優先使用'), ('models/gemini-flash-latest', '成本次低'), ('models/gemini-2.5-flash', '成本較高，當保底')]
清單內容/順序正確
payload: 假經文內容
嘗試順序: ['models/gemini-2.5-flash-lite', 'models/gemini-flash-latest']
```

- [ ] **Step 3: 修正 `main.py` 選單文字裡不準確的「免費模型」用詞**

原本（`main.py:25`）：
```python
MODEL_OPTIONS = {"自動（依序嘗試免費模型，推薦）": None}
```

換成：
```python
MODEL_OPTIONS = {"自動（依序嘗試，成本由低到高，推薦）": None}
```

- [ ] **Step 4: 手動驗證語法**

Run: `python -m py_compile main.py`
Expected: 沒有任何輸出。

- [ ] **Step 5: Commit**

```bash
git add bible_core.py main.py
git commit -m "fix: remove deprecated gemini-2.0-flash-lite, reorder candidates by cost"
```

---

## Task 2: `daily_push.py` — 全部候選失敗時通知管理員

**Files:**
- Modify: `daily_push.py`（整份重寫，加入 `ADMIN_USER_ID` 讀取與失敗通知邏輯）

**Interfaces:**
- Consumes：既有的 `bible_core.generate_verse`、`bible_core.send_line_message`、`bible_core.record_entry`、`bible_core.ID_FILE`（簽章皆不變）

- [ ] **Step 1: 重寫 `daily_push.py`**

原本：
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

    if not all([target_id, api_key, line_token]):
        return

    with open(bible_core.ID_FILE, "w") as f:
        f.write(target_id)

    try:
        payload, chosen_theme = bible_core.generate_verse(api_key)
        bible_core.send_line_message(line_token, target_id, f'【每日靈修】\n\n{payload}')
        bible_core.record_entry(payload, f"自動靈修-{chosen_theme}")
    except Exception as e:
        logger.error(f"系統錯誤: {e}")


if __name__ == "__main__":
    main()
```

換成：
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
    admin_user_id = os.environ.get('ADMIN_USER_ID', '').strip()

    if not all([target_id, api_key, line_token]):
        return

    with open(bible_core.ID_FILE, "w") as f:
        f.write(target_id)

    try:
        payload, chosen_theme = bible_core.generate_verse(api_key)
        bible_core.send_line_message(line_token, target_id, f'【每日靈修】\n\n{payload}')
        bible_core.record_entry(payload, f"自動靈修-{chosen_theme}")
    except Exception as e:
        logger.error(f"系統錯誤: {e}")
        if admin_user_id:
            try:
                bible_core.send_line_message(
                    line_token,
                    admin_user_id,
                    f'⚠️ 今日自動推播失敗\n所有 Gemini 模型都無法使用，請檢查額度/計費狀態。\n錯誤訊息：{e}'
                )
            except Exception as notify_error:
                logger.error(f"通知管理員失敗: {notify_error}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 手動驗證（假環境變數 + mock，涵蓋三種情境：全部失敗有通知、全部失敗但沒設定 ADMIN_USER_ID、正常成功）**

Run:
```bash
python -c "
import os
os.environ['TARGET_GROUP_ID'] = 'Cdummygroup'
os.environ['GEMINI_API_KEY'] = 'dummy'
os.environ['LINE_TOKEN'] = 'dummy'
os.environ['ADMIN_USER_ID'] = 'Uadmin123'
import daily_push
import bible_core
from unittest.mock import patch

# 情境一：全部模型失敗，且有設定 ADMIN_USER_ID -> 應該推一則通知給管理員
with patch.object(bible_core, 'generate_verse', side_effect=Exception('all models failed (fake)')) as gen, \
     patch.object(bible_core, 'send_line_message') as send, \
     patch.object(bible_core, 'record_entry') as record:
    daily_push.main()
    print('情境一 generate_verse called:', gen.called)
    print('情境一 send_line_message call count:', send.call_count)
    print('情境一 send_line_message args:', send.call_args)
    print('情境一 record_entry called:', record.called)

# 情境二：全部模型失敗，但沒設定 ADMIN_USER_ID -> 不應該嘗試通知
os.environ['ADMIN_USER_ID'] = ''
with patch.object(bible_core, 'generate_verse', side_effect=Exception('boom')), \
     patch.object(bible_core, 'send_line_message') as send:
    daily_push.main()
    print('情境二 send_line_message call count:', send.call_count)

# 情境三：正常成功 -> 只推播一次給 TARGET_GROUP_ID，不通知管理員
os.environ['ADMIN_USER_ID'] = 'Uadmin123'
with patch.object(bible_core, 'generate_verse', return_value=('假經文內容', '平安')), \
     patch.object(bible_core, 'send_line_message') as send, \
     patch.object(bible_core, 'record_entry') as record:
    daily_push.main()
    print('情境三 send_line_message call count:', send.call_count)
    print('情境三 send_line_message args:', send.call_args)
    print('情境三 record_entry called:', record.called)
"
```

Expected:
```
情境一 generate_verse called: True
情境一 send_line_message call count: 1
情境一 send_line_message args: call('dummy', 'Uadmin123', '⚠️ 今日自動推播失敗\n所有 Gemini 模型都無法使用，請檢查額度/計費狀態。\n錯誤訊息：all models failed (fake)')
情境一 record_entry called: False
情境二 send_line_message call count: 0
情境三 send_line_message call count: 1
情境三 send_line_message args: call('dummy', 'Cdummygroup', '【每日靈修】\n\n假經文內容')
情境三 record_entry called: True
```

- [ ] **Step 3: 手動驗證語法**

Run: `python -m py_compile daily_push.py`
Expected: 沒有任何輸出。

- [ ] **Step 4: Commit**

```bash
git add daily_push.py
git commit -m "feat: notify admin via LINE when all fallback models fail"
```

---

## Task 3: 更新 `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:** 無（純文件更新）

- [ ] **Step 1: 在「GitHub repo Secrets」清單加入 `ADMIN_USER_ID`**

原本（`CLAUDE.md:26-29`）：
```markdown
**GitHub repo Secrets**（已設定，供 `daily_push.py` 在 Actions 裡使用）：
- `LINE_TOKEN`
- `GEMINI_API_KEY`
- `TARGET_GROUP_ID`
```

換成：
```markdown
**GitHub repo Secrets**（供 `daily_push.py` 在 Actions 裡使用）：
- `LINE_TOKEN`
- `GEMINI_API_KEY`
- `TARGET_GROUP_ID`
- `ADMIN_USER_ID`：Brett 本人的 LINE User ID，跟 Render 上的值相同。用於全部候選模型都失敗時，`daily_push.py` 主動推播失敗通知給 Brett（2026-08-31 加入，之前這個 secret 只設在 Render）。
```

- [ ] **Step 2: 更新「Gemini 模型自動容錯」段落**

原本（`CLAUDE.md:44-46`）：
```markdown
## Gemini 模型自動容錯

`bible_core.py` 的 `FREE_MODEL_CANDIDATES` 是一份手動維護的免費模型優先順序清單，`generate_verse` 在沒有指定模型時會依序嘗試，一個撞到額度限制就換下一個。Google 常調整免費方案的額度規則，如果之後常常整批失敗（Render log 出現多行「模型 X 失敗」），要去 Google AI Studio 確認現在的免費額度規則，更新這份清單的內容或順序。`GEMINI_MODEL_NAME` 環境變數已經沒有作用了（Render／GitHub Actions 上如果還留著可以不用管，但不會被讀取）。
```

換成：
```markdown
## Gemini 模型自動容錯

`bible_core.py` 的 `FREE_MODEL_CANDIDATES` 是一份手動維護的模型優先順序清單（依已知單價由低到高排序），`generate_verse` 在沒有指定模型時會依序嘗試，一個失敗就換下一個。

**注意**：Brett 的 Google Cloud 專案是 **Tier 1**（已開通計費，不是完全免費），Gemini API 是否收費是專案層級設定，不是依模型名稱切換——這份清單能降低「單一模型下架或出問題」造成整批失敗的風險，但無法讓呼叫變成真正免費。額度/計費狀態可以到 https://aistudio.google.com/spend 查看目前的每月支出上限與用量。

如果之後常常整批失敗（GitHub Actions/Render log 出現多行「模型 X 失敗」），除了檢查上面那個支出上限頁面，也要去 Google AI Studio 確認模型是否又被下架或改名（2026-08 曾發生 `models/gemini-2.0-flash-lite` 被下架導致整批失敗），更新這份清單的內容或順序。`GEMINI_MODEL_NAME` 環境變數已經沒有作用了（Render／GitHub Actions 上如果還留著可以不用管，但不會被讀取）。

`daily_push.py` 在所有候選模型都失敗時，會額外推一則 LINE 訊息通知 `ADMIN_USER_ID`（需要在 GitHub repo Secrets 也設定這個值，見上面「GitHub repo Secrets」清單），避免像 2026-08-31 那次一樣連續多天失敗都沒人發現。
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document Tier 1 billing reality and admin failure notification"
```

---

## Task 4（人工執行，非 subagent）：Brett 補設定並驗證

這個任務需要 GitHub repo 後台存取權，subagent 沒有這個權限，必須由 Brett 本人完成。

- [ ] Push 所有 commit 到 GitHub
- [ ] 到 GitHub repo 的 Settings → Secrets and variables → Actions，新增一個 Secret：`ADMIN_USER_ID`，值跟 Render 上設定的一樣（Brett 自己的 LINE User ID）
- [ ] 手動觸發一次 `daily_push.yml`（GitHub Actions 頁面點 workflow_dispatch），確認：
  - 正常情況下能收到經文推播，且 `bible_history.json` 有新紀錄
  - （選擇性測試，不一定要做）如果想驗證失敗通知邏輯本身，可以暫時把 GitHub Secret 的 `GEMINI_API_KEY` 改成無效值觸發一次失敗，確認會收到「⚠️ 今日自動推播失敗」的 LINE 訊息，測試完記得把 `GEMINI_API_KEY` 改回正確值
- [ ] 觀察接下來幾天，確認每天都正常收到推播，或者收到失敗通知（而不是像這次一樣完全沒反應）

## Self-Review Notes

**Spec coverage：** 清單移除下架模型、重新依成本排序 ✅（Task 1），全部失敗通知管理員 ✅（Task 2），通知失敗不影響既有錯誤處理 ✅（Task 2 nested try/except），app.py 不新增通知邏輯 ✅（未在任何 Task 中修改 app.py），CLAUDE.md 記錄 Tier 1 現實與新 Secret ✅（Task 3），Brett 需要手動加 GitHub Secret ✅（Task 4）。

**Type consistency：** `bible_core.send_line_message(line_token, target_id, message_text)` 簽章在 Task 2 兩處呼叫（原本的推播 + 新的管理員通知）都對齊，跟既有定義一致，未變更。`FREE_MODEL_CANDIDATES` 結構在 Task 1 前後都是 `list[tuple[str, str]]`，`generate_verse` 的解構邏輯（`for candidate_name, _label in FREE_MODEL_CANDIDATES`）不需要跟著改。
