import os
import json
import random
import subprocess
import logging
from datetime import datetime, timezone, timedelta
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 日誌初始化 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# 使用絕對路徑
BASE_DIR = os.getcwd()
DB_FILE = os.path.join(BASE_DIR, "bible_history.json")
TZ_TW = timezone(timedelta(hours=8))

def main():
    logger.info("【階段 1】程式啟動")
    
    target_id = os.environ.get('TARGET_GROUP_ID', '').strip()
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    line_token = os.environ.get('LINE_TOKEN', '').strip()
    
    if not all([target_id, api_key, line_token]):
        logger.error("❌ 環境變數缺失")
        return

    # 1. Gemini 生成
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-flash-latest')
        themes = ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"]
        prompt = f"請針對主題「{random.choice(themes)}」，精選一段聖經經文。格式：【內容】；【章節】；【領受】。"
        res = model.generate_content(prompt)
        payload = res.text.strip()
    except Exception as e:
        logger.error(f"❌ Gemini 故障: {e}")
        return

    # 2. LINE 推送
    try:
        line_api = LineBotApi(line_token)
        line_api.push_message(target_id, TextSendMessage(text=f'【每日靈修】\n\n{payload}'))
    except Exception as e:
        logger.error(f"❌ LINE 推送失敗: {e}")
        return

    # 3. 資料庫更新
    data = []
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try: data = json.load(f)
            except: data = []
    
    data.insert(0, {"date": datetime.now(TZ_TW).strftime("%Y-%m-%d"), "time": datetime.now(TZ_TW).strftime("%H:%M:%S"), "category": "每日靈修", "content": payload})
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logger.info("【階段 6】資料庫已本地更新")

    # 4. 強制 Git 同步
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
        subprocess.run(["git", "add", DB_FILE], check=True)
        subprocess.run(["git", "commit", "-m", "Auto-sync bible history"], check=True)
        
        remote_url = f"https://x-access-token:{os.environ.get('GITHUB_TOKEN')}@github.com/{os.environ.get('GITHUB_REPOSITORY')}.git"
        # 使用 HEAD:main 強制將當前提交推送到 main 分支
        subprocess.run(["git", "push", remote_url, "HEAD:main", "--force"], check=True)
        logger.info("【階段 7】Git 同步成功，UI 將同步更新")
    except Exception as e:
        logger.error(f"❌ Git 同步失敗: {e}")

if __name__ == "__main__":
    main()
