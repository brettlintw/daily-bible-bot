import os
import json
import random
import logging
from datetime import datetime, timezone, timedelta
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = os.getcwd()
DB_FILE = os.path.join(BASE_DIR, "bible_history.json")
ID_FILE = os.path.join(BASE_DIR, "latest_group_id.txt")
TZ_TW = timezone(timedelta(hours=8))

def main():
    target_id = os.environ.get('TARGET_GROUP_ID', '').strip()
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    line_token = os.environ.get('LINE_TOKEN', '').strip()
    model_name = os.environ.get('GEMINI_MODEL_NAME', 'models/gemini-flash-latest')
    
    if not all([target_id, api_key, line_token]):
        return

    # 1. 紀錄最新 ID
    with open(ID_FILE, "w") as f:
        f.write(target_id)

    # 2. 生成與推送
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        themes = ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"]
        prompt = f"請針對主題「{random.choice(themes)}」，精選一段聖經經文。格式：【內容】；【章節】；【領受】。"
        res = model.generate_content(prompt)
        payload = res.text.strip()
        
        line_api = LineBotApi(line_token)
        line_api.push_message(target_id, TextSendMessage(text=f'【每日靈修】\n\n{payload}'))
        
        # 3. 更新資料庫
        data = []
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                try: data = json.load(f)
                except: data = []
        data.insert(0, {"date": datetime.now(TZ_TW).strftime("%Y-%m-%d"), "time": datetime.now(TZ_TW).strftime("%H:%M:%S"), "category": "自動靈修", "content": payload})
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
    except Exception as e:
        logger.error(f"系統錯誤: {e}")

if __name__ == "__main__":
    main()
