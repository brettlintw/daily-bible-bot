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

    # 2. 讀取歷史以確保多樣性 (擴大至最後 30 筆)
    history_titles = []
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                # 取前 30 筆紀錄來建立「黑名單」
                history_titles = [item.get("content", "")[:60] for item in data[:30]]
            except: pass
    
    history_str = "\n".join(history_titles)

    # 3. 生成與推送
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        themes = ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"]
        chosen_theme = random.choice(themes)
        
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
        
        res = model.generate_content(prompt)
        payload = res.text.strip()
        
        line_api = LineBotApi(line_token)
        line_api.push_message(target_id, TextSendMessage(text=f'【每日靈修】\n\n{payload}'))
        
        # 4. 更新資料庫
        data = []
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                try: data = json.load(f)
                except: data = []
        data.insert(0, {"date": datetime.now(TZ_TW).strftime("%Y-%m-%d"), "time": datetime.now(TZ_TW).strftime("%H:%M:%S"), "category": f"自動靈修-{chosen_theme}", "content": payload})
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
    except Exception as e:
        logger.error(f"系統錯誤: {e}")

if __name__ == "__main__":
    main()
