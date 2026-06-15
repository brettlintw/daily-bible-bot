import os
import json
import random
import subprocess
import shutil
from datetime import datetime, timezone, timedelta
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage

DB_FILE = "bible_history.json"
TZ_TW = timezone(timedelta(hours=8))

def main():
    genai.configure(api_key=os.environ['GEMINI_API_KEY'])
    model = genai.GenerativeModel('gemini-2.5-flash')
    line_api = LineBotApi(os.environ['LINE_TOKEN'])

    # 1. 生成與推送
    themes = ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"]
    payload = model.generate_content(f"請針對主題「{random.choice(themes)}」，精選一段聖經經文分享。格式：【經文內容】(阿們。)；【經文章節】；【領受與感悟】。").text.strip()

    # 2. 推送 (這裡維持原樣，待您之後填入群組ID)
    target_id = 'Uf166c741223bc8ee5d82fd1fd9f4df86'
    line_api.push_message(target_id, TextSendMessage(text=f'【每日靈修】\n\n{payload}'))

    # 3. 更新 JSON
    data = []
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f: data = json.load(f)
    data.insert(0, {"date": datetime.now(TZ_TW).strftime("%Y-%m-%d"), "content": payload})
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

    # 4. Git 同步 (加上了變更檢查)
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions@github.com"], check=True)
        subprocess.run(["git", "add", DB_FILE], check=True)
        
        # 關鍵：檢查是否有檔案被修改
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if DB_FILE in status.stdout:
            subprocess.run(["git", "commit", "-m", "Auto-sync bible history"], check=True)
            subprocess.run(["git", "push", "origin", "main"], check=True)
            print("Git 同步完成")
        else:
            print("目前已是最新狀態，無需同步。")
    except Exception as e:
        print(f"Git 同步過程遇到問題，但已處理: {e}")

if __name__ == "__main__":
    main()
