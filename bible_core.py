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

logger = logging.getLogger(__name__)

TZ_TW = timezone(timedelta(hours=8))
DB_FILE = "bible_history.json"
ID_FILE = "latest_group_id.txt"
THEMES = ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心", "感恩", "喜樂", "忍耐", "謙卑", "引導"]

FREE_MODEL_CANDIDATES = [
    ("models/gemini-2.5-flash-lite", "成本最低，優先使用"),
    ("models/gemini-flash-latest", "成本次低"),
    ("models/gemini-2.5-flash", "成本較高，當保底"),
]

REFERENCE_PATTERN = re.compile(r'《[^》]+》[^；\n]*')

BIBLE_BOOKS = [
    "創世記", "出埃及記", "利未記", "民數記", "申命記", "約書亞記", "士師記", "路得記", "撒母耳記上", "撒母耳記下",
    "列王紀上", "列王紀下", "歷代志上", "歷代志下", "以斯拉記", "尼希米記", "以斯帖記", "約伯記", "詩篇", "箴言",
    "傳道書", "雅歌", "以賽亞書", "耶利米書", "耶利米哀歌", "以西結書", "但以理書", "何西阿書", "約珥書", "阿摩司書",
    "俄巴底亞書", "約拿書", "彌迦書", "那鴻書", "哈巴谷書", "西番雅書", "哈該書", "撒迦利亞書", "瑪拉基書",
    "馬太福音", "馬可福音", "路加福音", "約翰福音", "使徒行傳", "羅馬書", "哥林多前書", "哥林多後書", "加拉太書",
    "以弗所書", "腓立比書", "歌羅西書", "帖撒羅尼迦前書", "帖撒羅尼迦後書", "提摩太前書", "提摩太後書", "提多書",
    "腓利門書", "希伯來書", "雅各書", "彼得前書", "彼得後書", "約翰一書", "約翰二書", "約翰三書", "猶大書", "啟示錄",
]
_NUM = r'[\d零一二三四五六七八九十百]+'
# Fallback for when Gemini ignores the 《書卷》 format, e.g. 【彼得前書】5:7 or 「羅馬書 15:13」
BOOK_REFERENCE_PATTERN = re.compile(
    r'(' + '|'.join(sorted(BIBLE_BOOKS, key=len, reverse=True)) + r')'
    r'[】》\s*]*第?\s*(' + _NUM + r')\s*[章篇:：]\s*(' + _NUM + r'(?:\s*[-–—至]\s*' + _NUM + r')?)'
)


def extract_reference(content):
    match = REFERENCE_PATTERN.search(content)
    if match:
        return match.group(0).strip()
    # Only look before the 領受 section so a book name quoted in the commentary can't match
    scripture_part = re.split(r'【領受', content, maxsplit=1)[0]
    match = BOOK_REFERENCE_PATTERN.search(scripture_part)
    if match:
        book, chapter, verses = match.groups()
        return f"《{book}》{chapter}:{verses}"
    return None


_CN_DIGITS = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
_CN_UNITS = {'十': 10, '百': 100}
_CN_NUM_PATTERN = re.compile(r'[零一二三四五六七八九十百]+')


def _cn_num_to_arabic(cn_num_str):
    total = 0
    section = 0
    num = 0
    for ch in cn_num_str:
        if ch in _CN_DIGITS:
            num = _CN_DIGITS[ch]
        elif ch in _CN_UNITS:
            unit = _CN_UNITS[ch]
            if num == 0:
                num = 1
            section += num * unit
            num = 0
    section += num
    total += section
    return str(total)


def normalize_reference(ref):
    if ref is None:
        return None
    ref = re.sub(r'《[^》]*[·・]', '《', ref)
    # Split off the 《book title》 portion so label-stripping below never touches
    # characters that are part of the book name itself (e.g. "詩篇", "約翰一書").
    if '》' in ref:
        book, rest = ref.split('》', 1)
        book += '》'
    else:
        book, rest = '', ref
    rest = _CN_NUM_PATTERN.sub(lambda m: _cn_num_to_arabic(m.group(0)), rest)
    rest = rest.replace('至', '-').replace('第', '').replace('章', ':').replace('篇', ':').replace('節', '')
    return re.sub(r'\s+', '', book + rest)


def get_recent_references(months=5, db_file=DB_FILE):
    cutoff = datetime.now(TZ_TW) - timedelta(days=30 * months)
    cutoff_date_str = cutoff.strftime("%Y-%m-%d")
    refs = set()
    for entry in load_history(db_file):
        if entry.get("date", "") >= cutoff_date_str:
            ref = extract_reference(entry.get("content", ""))
            if ref:
                refs.add(normalize_reference(ref))
    return refs


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


def _generate_once(api_key, model_name, chosen_theme, avoid_refs, dedup_months):
    genai.configure(api_key=api_key)

    avoid_str = "\n".join(sorted(avoid_refs)) if avoid_refs else "（無）"

    prompt = f"""
    你是一位充滿智慧的資深牧者。
    請精選一段聖經經文。
    主題選擇：{chosen_theme}。

    【絕對禁令】：嚴禁輸出與下方清單相同的經文章節。
    這是一份最近 {dedup_months} 個月已經分享過的經文章節清單 (請避開以下所有章節)：
    {avoid_str}

    請依照此格式嚴格輸出，【章節】必須寫成《書卷名》章:節 (例如《彼得前書》5:7)：
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
        payload = _generate_once(api_key, model_name, chosen_theme, avoid_refs, dedup_months)
        ref = extract_reference(payload)
        last_payload, last_theme = payload, chosen_theme

        if ref is not None and normalize_reference(ref) not in avoid_refs:
            return payload, chosen_theme

        if ref is None:
            logger.error(f"第 {attempt} 次生成無法辨識章節，無法驗證是否重複，重打")
        else:
            logger.error(f"第 {attempt} 次生成撞到重複經文（{ref}），重打")

    logger.error(f"重試 {max_attempts} 次仍重複，直接採用最後一次結果")
    return last_payload, last_theme


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
