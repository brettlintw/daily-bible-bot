import os
import json
import random
import subprocess
import shutil
from datetime import datetime, timezone, timedelta
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage
from tenacity import retry, stop_after_attempt, wait_exponential

# --- 設定 ---
DB_FILE = "bible_history.json"
TZ_TW = timezone(timedelta(hours=8))
PERSONAL_USER_ID = os.environ.get('PERSONAL_USER_ID')

# 加上重試邏輯：遇到 ResourceExhausted 會自動等待重試 (最小等待 4 秒，最大 60 秒)
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=60))
def call_gemini_with_retry(model, prompt):
    return model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.8))

def main():
    # 1. 初始化
    genai.configure(api_key=os.environ['GEMINI_API_KEY'])
    model = genai.GenerativeModel('gemini-2.5-flash')

    # 2. 生成內容 (調用重試函式)
    themes = ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"]
    chosen_theme = random.choice(themes)
    prompt = f"你是溫柔牧者。請針對主題「{chosen_theme}」，精選一段聖經經文進行分享。格式：【經文內容】(阿們。)；【經文章節】；【領受與感悟】。禁止贅字，內容完整禁止斷章。"

    try:
        res = call_gemini_with_retry(model, prompt)
        payload = res.text.strip()
    except Exception as e:
        print(f"❌ Gemini 生成失敗 (已重試三次): {e}")
        return

    # 3. 推送至個人 LINE
    line_api = LineBotApi(os.environ['LINE_TOKEN'])
    line_api.push_message(PERSONAL_USER_ID, TextSendMessage(text=f'【每日靈修】\n\n{payload}'))

    # 4. 安全地寫入 JSON
    data = []
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except: data = []
    
    data.insert(0, {
        "date": datetime.now(TZ_TW).strftime("%Y-%m-%d"),
        "time": datetime.now(TZ_TW).strftime("%H:%M:%S"),
        "category": f"自動推播-{chosen_theme}",
        "content": payload
    })
    
    temp_file = DB_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    shutil.move(temp_file, DB_FILE)

    # 5. Git 自動同步
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions@github.com"], check=True)
        subprocess.run(["git", "add", DB_FILE], check=True)
        
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if DB_FILE in status.stdout:
            subprocess.run(["git", "commit", "-m", "Auto-sync bible history"], check=True)
            branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
            subprocess.run(["git", "push", "origin", branch], check=True)
            print(f"歷史紀錄已成功推送到分支: {branch}")
        else:
            print("無數據變動，無需同步。")
    except Exception as e:
        print(f"Git 同步失敗: {e}")

if __name__ == "__main__":
    main()
