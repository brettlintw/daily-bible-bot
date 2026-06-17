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

# --- 日誌初始化 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_FILE = "bible_history.json"
TZ_TW = timezone(timedelta(hours=8))

# 終極清洗函數：強制移除所有非 ASCII 字符 (徹底過濾雜訊)
def clean_str(s):
    return s.encode('ascii', 'ignore').decode('ascii').strip()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def call_gemini_with_retry(model, prompt):
    return model.generate_content(prompt)

def main():
    logger.info("啟動每日靈修推播程序...")
    
    target_id = clean_str(os.environ.get('TARGET_GROUP_ID', ''))
    if not target_id:
        logger.error("❌ 未設定 TARGET_GROUP_ID")
        return

    # 1. 初始化 (應用終極清洗)
    genai.configure(api_key=clean_str(os.environ.get('GEMINI_API_KEY', '')))
    model = genai.GenerativeModel('gemini-1.5-flash')
    line_api = LineBotApi(clean_str(os.environ.get('LINE_TOKEN', '')))

    # 2. 生成內容
    themes = ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"]
    chosen_theme = random.choice(themes)
    prompt = f"你是溫柔牧者。請針對主題「{chosen_theme}」，精選一段聖經經文。格式：【經文內容】(阿們。)；【章節】；【領受與感悟】。"

    try:
        res = call_gemini_with_retry(model, prompt)
        payload = res.text.strip()
        logger.info(f"成功生成主題: {chosen_theme}")
    except Exception as e:
        logger.error(f"❌ Gemini 故障: {e}")
        return

    # 3. 推送
    try:
        line_api.push_message(target_id, TextSendMessage(text=f'【每日靈修】\n\n{payload}'))
        logger.info("LINE 推送成功")
    except Exception as e:
        logger.error(f"❌ LINE 推送失敗: {e}")
        return

    # 4. 更新資料庫
    data = []
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try: data = json.load(f)
            except: data = []
    
    data.insert(0, {"date": datetime.now(TZ_TW).strftime("%Y-%m-%d"), "category": f"自動推播-{chosen_theme}", "content": payload})
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # 5. Git 同步 (強效靜默與逾時控制)
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True, timeout=10)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True, timeout=10)
        subprocess.run(["git", "add", DB_FILE], check=True, timeout=10)
        
        if subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, timeout=10).stdout:
            subprocess.run(["git", "commit", "-m", "Auto-sync bible history"], check=True, timeout=10)
            
            logger.info("準備 Git Push...")
            remote_url = f"https://x-access-token:{os.environ.get('GITHUB_TOKEN')}@github.com/{os.environ.get('GITHUB_REPOSITORY')}.git"
            # 增加 timeout 與 --quiet，確保不卡死且不輸出敏感憑證
            subprocess.run(["git", "push", remote_url, "main", "--quiet"], check=True, timeout=30)
            logger.info("同步至 GitHub 成功")
    except Exception as e:
        logger.error(f"❌ Git 同步異常: {e}")

if __name__ == "__main__":
    main()
