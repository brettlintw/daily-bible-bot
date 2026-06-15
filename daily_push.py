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

    # 1. 生成經文
    themes = ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"]
    chosen_theme = random.choice(themes)
    prompt = f"你是溫柔牧者。請針對主題「{chosen_theme}」，精選一段聖經經文分享。格式：【經文內容】(阿們。)；【經文章節】；【領受與感悟】。禁止贅字，內容完整禁止斷章。"
    res = model.generate_content(prompt)
    payload = res.text.strip()

    # 2. 推送 (目標 ID 之後再填入群組ID)
    target_id = 'Uf166c741223bc8ee5d82fd1fd9f4df86'
    line_api.push_message(target_id, TextSendMessage(text=f'【每日靈修】\n\n{payload}'))

    # 3. 處理 JSON 檔案
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
    
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # 4. 強制同步區塊 (最穩定版)
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions@github.com"], check=True)
        
        # 捨棄所有本地修改，強制拉取最新並覆蓋
        subprocess.run(["git", "fetch", "origin", "main"], check=True)
        subprocess.run(["git", "reset", "--hard", "origin/main"], check=True)
        
        # 重新加入修改後的檔案
        subprocess.run(["git", "add", DB_FILE], check=True)
        subprocess.run(["git", "commit", "-m", "Auto-sync bible history"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("Git 同步完成")
    except Exception as e:
        print(f"Git 同步失敗，但已完成推送: {e}")

if __name__ == "__main__":
    main()
