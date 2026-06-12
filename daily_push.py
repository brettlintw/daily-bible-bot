import os
import json
import random
import time
import subprocess
from datetime import datetime, timezone, timedelta
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage

DB_FILE = "bible_history.json"
TZ_TW = timezone(timedelta(hours=8))

# 1. 初始化
genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash')

# 2. 生成與發送
themes = ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"]
chosen_theme = random.choice(themes)
prompt = f"你是溫柔牧者，針對主題「{chosen_theme}」，精選聖經經文分享。格式：【經文內容】(阿們。)；【經文章節】；【領受與感悟】。禁止贅字，總字數 600 字內。"

res = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.8))
payload = res.text.strip()

line_api = LineBotApi(os.environ['LINE_TOKEN'])
line_api.push_message('Uf166c741223bc8ee5d82fd1fd9f4df86', TextSendMessage(text=f'【每日靈修】\n\n{payload}'))

# 3. 儲存與 Git 同步
data = []
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

data.insert(0, {"date": datetime.now(TZ_TW).strftime("%Y-%m-%d"), "time": datetime.now(TZ_TW).strftime("%H:%M:%S"), "category": f"自動推播-{chosen_theme}", "content": payload})

with open(DB_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

# 自動回寫到 GitHub
subprocess.run(["git", "config", "--global", "user.name", "github-actions"])
subprocess.run(["git", "config", "--global", "user.email", "github-actions@github.com"])
subprocess.run(["git", "add", DB_FILE])
subprocess.run(["git", "commit", "-m", "Sync bible history"])
subprocess.run(["git", "push"])
