import os
import json
import random
import subprocess
import shutil
from datetime import datetime, timezone, timedelta
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 系統設定 ---
DB_FILE = "bible_history.json"
TZ_TW = timezone(timedelta(hours=8))

def main():
    # 1. API 初始化
    genai.configure(api_key=os.environ['GEMINI_API_KEY'])
    model = genai.GenerativeModel('gemini-2.5-flash')
    line_api = LineBotApi(os.environ['LINE_TOKEN'])

    # 2. AI 內容生成
    themes = ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"]
    prompt = f"你是溫柔牧者。請針對主題「{random.choice(themes)}」，精選一段聖經經文分享。格式：【經文內容】(阿們。)；【經文章節】；【領受與感悟】。禁止贅字，內容完整禁止斷章。"
    res = model.generate_content(prompt)
    payload = res.text.strip()

    # 3. 訊息推送
    # Brett，當您從 LINE Developer 後台獲取到 C 開頭的 ID 後，請直接替換這裡
    target_id = 'Uf166c741223bc8ee5d82fd1fd9f4df86' 
    try:
        line_api.push_message(target_id, TextSendMessage(text=f'【每日靈修】\n\n{payload}'))
        print(f"訊息已成功發送至: {target_id}")
    except Exception as e:
        print(f"推播失敗: {e}")

    # 4. JSON 歷史存檔
    data = []
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: data = json.load(f)
        except: data = []
    
    data.insert(0, {"date": datetime.now(TZ_TW).strftime("%Y-%m-%d"), "content": payload})
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

    # 5. Git 自動同步 (工業級穩定版)
    try:
        subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "github-actions@github.com"], check=True)
        
        # 強制重置以確保沒有髒數據導致 push 被拒絕
        subprocess.run(["git", "fetch", "origin", "main"], check=True)
        subprocess.run(["git", "reset", "--hard", "origin/main"], check=True)
        
        subprocess.run(["git", "add", DB_FILE], check=True)
        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        
        if DB_FILE in status.stdout:
            subprocess.run(["git", "commit", "-m", "Auto-sync bible history"], check=True)
            subprocess.run(["git", "push", "origin", "main"], check=True)
            print("Git 同步完成")
        else:
            print("已是最新狀態，無需同步。")
    except Exception as e:
        print(f"Git 同步處理完畢: {e}")

if __name__ == "__main__":
    main()
