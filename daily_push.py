import os
import json
import random
import subprocess
import shutil
import logging
from datetime import datetime, timezone, timedelta
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 日誌初始化 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

DB_FILE = "bible_history.json"
TZ_TW = timezone(timedelta(hours=8))

def main():
    logger.info("【階段 1】程式啟動")
    
    target_id = os.environ.get('TARGET_GROUP_ID', '').strip()
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    line_token = os.environ.get('LINE_TOKEN', '').strip()
    
    if not all([target_id, api_key, line_token]):
        logger.error("❌ 環境變數缺失")
        return
    logger.info("【階段 2】環境變數讀取完畢")

    # 1. Gemini 初始化測試
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("【階段 3】Gemini 客戶端初始化完成")
        
        # 生成內容
        themes = ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"]
        prompt = f"你是溫柔牧者。請針對主題「{random.choice(themes)}」，精選一段聖經經文。格式：【內容】；【章節】；【領受】。"
        res = model.generate_content(prompt)
        payload = res.text.strip()
        logger.info("【階段 4】內容生成完成")
    except Exception as e:
        logger.error(f"【階段 4】Gemini 故障: {e}")
        return

    # 2. LINE 推送測試
    try:
        line_api = LineBotApi(line_token)
        line_api.push_message(target_id, TextSendMessage(text=f'【每日靈修】\n\n{payload}'))
        logger.info("【階段 5】LINE 推送完成")
    except Exception as e:
        logger.error(f"【階段 5】LINE 推送失敗: {e}")
        return

    # 3. 資料庫更新
    data = []
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try: data = json.load(f)
            except: data = []
    
    data.insert(0, {"date": datetime.now(TZ_TW).strftime("%Y-%m-%d"), "category": "測試", "content": payload})
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logger.info("【階段 6】資料庫寫入完成")

    # 4. Git 同步 (已完全關閉，驗證是否為卡死原因)
    logger.info("【階段 7】Git 同步已暫時關閉，驗證程序結束")

if __name__ == "__main__":
    main()
