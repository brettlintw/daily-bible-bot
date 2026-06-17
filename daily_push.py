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
    
    # 讀取與驗證環境變數
    target_id = os.environ.get('TARGET_GROUP_ID', '').strip()
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    line_token = os.environ.get('LINE_TOKEN', '').strip()
    
    if not all([target_id, api_key, line_token]):
        logger.error("❌ 環境變數缺失 (確認 TARGET/GEMINI/LINE 是否已設定)")
        return
    logger.info("【階段 2】環境變數讀取完畢")

    # Gemini 初始化測試
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("【階段 3】Gemini 客戶端初始化完成")
        
        # 進行輕量化測試連線
        test_res = model.generate_content("Hi")
        logger.info("【階段 4】Gemini 連線成功")
    except Exception as e:
        logger.error(f"【階段 4】Gemini 連線失敗: {e}")
        return

    # LINE 推送測試
    try:
        line_api = LineBotApi(line_token)
        # 生成內容
        themes = ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"]
        prompt = f"請針對主題「{random.choice(themes)}」，精選一段聖經經文。格式：【內容】；【章節】；【領受】。"
        res = model.generate_content(prompt)
        payload = res.text.strip()
        
        line_api.push_message(target_id, TextSendMessage(text=f'【測試推播】\n\n{payload}'))
        logger.info("【階段 5】LINE 推送完成")
    except Exception as e:
        logger.error(f"【階段 5】LINE 推送失敗: {e}")
        return

    # Git 同步 (階段性日誌)
    logger.info("【階段 6】開始執行 Git 同步")
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True, timeout=10)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True, timeout=10)
        subprocess.run(["git", "add", "."], check=True, timeout=10)
        
        if subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, timeout=10).stdout:
            subprocess.run(["git", "commit", "-m", "Auto-sync"], check=True, timeout=10)
            
            logger.info("準備執行 Git Push...")
            remote_url = f"https://x-access-token:{os.environ.get('GITHUB_TOKEN')}@github.com/{os.environ.get('GITHUB_REPOSITORY')}.git"
            subprocess.run(["git", "push", remote_url, "main", "--quiet"], check=True, timeout=30)
            logger.info("【階段 7】Git 同步成功")
    except Exception as e:
        logger.error(f"【階段 6/7】Git 操作失敗: {e}")

if __name__ == "__main__":
    main()
