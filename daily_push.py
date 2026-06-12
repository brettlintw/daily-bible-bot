import os
import json
import random
import time
import subprocess
import shutil
from datetime import datetime, timezone, timedelta
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage

DB_FILE = "bible_history.json"
TZ_TW = timezone(timedelta(hours=8))

def main():
    # 1. 初始化
    genai.configure(api_key=os.environ['GEMINI_API_KEY'])
    model = genai.GenerativeModel('gemini-2.5-flash')

    # 2. 生成內容
    themes = ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"]
    chosen_theme = random.choice(themes)
    prompt = f"你是溫柔牧者。請針對主題「{chosen_theme}」，精選一段聖經經文進行分享。格式：【經文內容】(阿們。)；【經文章節】；【領受與感悟】。禁止贅字，內容完整禁止斷章。"

    res = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.8))
    payload = res.text.strip()

    # 3. 推送至 LINE
    line_api = LineBotApi(os.environ['LINE_TOKEN'])
    line_api.push_message('Uf166c741223bc8ee5d82fd1fd9f4df86', TextSendMessage(text=f'【每日靈修】\n\n{payload}'))

    # 4. 安全地寫入 JSON (使用暫存檔替換)
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

# 5. Git 自動同步 (修正版：自動偵測當前分支)
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions@github.com"], check=True)
        subprocess.run(["git", "add", DB_FILE], check=True)
        
        # 檢查是否有變動
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if DB_FILE in status.stdout:
            subprocess.run(["git", "commit", "-m", "Auto-sync bible history"], check=True)
            
            # 自動取得當前分支名稱 (通常是 main 或 master)
            branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
            subprocess.run(["git", "push", "origin", branch], check=True)
            print(f"歷史紀錄已成功推送到分支: {branch}")
        else:
            print("無數據變動，無需同步。")
    except Exception as e:
        print(f"Git 同步失敗: {e}")

if __name__ == "__main__":
    main()
