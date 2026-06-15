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
from tenacity import retry, stop_after_attempt, wait_exponential

# --- 1. 日誌初始化 (工業級監控) ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 設定 ---
DB_FILE = "bible_history.json"
TZ_TW = timezone(timedelta(hours=8))
PERSONAL_USER_ID = os.environ.get('PERSONAL_USER_ID')

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def call_gemini_with_retry(model, prompt):
    return model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.8))

def main():
    logger.info("啟動每日靈修推播程序...")
    
    # 1. 初始化
    genai.configure(api_key=os.environ['GEMINI_API_KEY'])
    model = genai.GenerativeModel('gemini-2.5-flash')
    line_api = LineBotApi(os.environ['LINE_TOKEN'])

    # 2. 生成內容
    themes = ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"]
    chosen_theme = random.choice(themes)
    prompt = f"你是溫柔牧者。請針對主題「{chosen_theme}」，精選一段聖經經文。格式：【經文內容】(阿們。)；【章節】；【領受與感悟】。"

    try:
        res = call_gemini_with_retry(model, prompt)
        payload = res.text.strip()
        logger.info(f"成功生成主題: {chosen_theme}")
    except Exception as e:
        error_msg = f"❌ Gemini 系統故障: {e}"
        logger.error(error_msg)
        line_api.push_message(PERSONAL_USER_ID, TextSendMessage(text=f"⚠️ {error_msg}"))
        return

    # 3. 推送至個人 LINE
    try:
        line_api.push_message(PERSONAL_USER_ID, TextSendMessage(text=f'【每日靈修】\n\n{payload}'))
        logger.info("成功推送至 LINE")
    except Exception as e:
        logger.error(f"❌ LINE 推送失敗: {e}")
        return

    # 4. 資料庫更新
    data = []
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try: data = json.load(f)
            except: data = []
    
    data.insert(0, {
        "date": datetime.now(TZ_TW).strftime("%Y-%m-%d"),
        "time": datetime.now(TZ_TW).strftime("%H:%M:%S"),
        "category": f"自動推播-{chosen_theme}",
        "content": payload
    })
    
    with open(DB_FILE + ".tmp", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    shutil.move(DB_FILE + ".tmp", DB_FILE)

    # 5. Git 自動同步 (加入日誌紀錄)
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions@github.com"], check=True)
        subprocess.run(["git", "add", DB_FILE], check=True)
        
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if DB_FILE in status.stdout:
            subprocess.run(["git", "commit", "-m", "Auto-sync bible history"], check=True)
            subprocess.run(["git", "push", "origin", "main"], check=True) # 強制推送到 main 分支
            logger.info("歷史紀錄已成功同步至 GitHub")
        else:
            logger.info("無數據變動，無需同步。")
    except Exception as e:
        logger.error(f"❌ Git 同步嚴重異常: {e}")

if __name__ == "__main__":
    main()
