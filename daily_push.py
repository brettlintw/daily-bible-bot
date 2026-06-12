import os
import json
import random
import time
from datetime import datetime, timezone, timedelta
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 設定 ---
DB_FILE = "bible_history.json"
TZ_TW = timezone(timedelta(hours=8))

def save_to_history(content, category):
    """將推播內容存入 JSON，以便 UI 讀取"""
    data = []
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except: pass
    
    data.insert(0, {
        "date": datetime.now(TZ_TW).strftime("%Y-%m-%d"),
        "time": datetime.now(TZ_TW).strftime("%H:%M:%S"),
        "category": category,
        "content": content
    })
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 1. 初始化
genai.configure(api_key=os.environ['GEMINI_API_KEY'])
# 強制連結至生產環境穩定的 2.5 版本
model = genai.GenerativeModel('gemini-2.5-flash')

# 2. 生成內容 (加入隨機性與歷史意識)
themes = ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"]
chosen_theme = random.choice(themes)

prompt = f"""
你是溫柔牧者。請針對主題「{chosen_theme}」，精選一段聖經經文進行分享。
格式嚴格要求：
【經文內容】
(經文內容，最後手動加上 (阿們。))
【經文章節】
(例如：(詩篇 4:8))
【領受與感悟】
(撰寫一段深度溫暖的靈修反思)
鐵律：禁止贅字，總字數 600 字內，內容完整禁止斷章。
"""

# 使用重試機制處理可能的 API 延遲
for attempt in range(3):
    try:
        res = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.8))
        payload = res.text.strip()
        break
    except Exception as e:
        if attempt == 2: raise e
        time.sleep(5)

# 3. 推送至 LINE
line_api = LineBotApi(os.environ['LINE_TOKEN'])
line_api.push_message('Uf166c741223bc8ee5d82fd1fd9f4df86', TextSendMessage(text=f'【每日靈修】\n\n{payload}'))

# 4. 同步至 UI 歷史紀錄
save_to_history(payload, f"自動推播-{chosen_theme}")

print('發送成功且紀錄已同步！')
