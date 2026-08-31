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

FREE_MODEL_CANDIDATES = [
    ("models/gemini-2.5-flash-lite", "成本最低，優先使用"),
    ("models/gemini-flash-latest", "成本次低"),
    ("models/gemini-2.5-flash", "成本較高，當保底"),
]


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
