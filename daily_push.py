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
    line_api = LineBotApi(os.environ['LINE_TOKEN'])

    # --- 【除錯模式】：抓取群組 ID ---
    # 當您在群組對 Bot 發言後，Webhook 會記錄資訊。
    # 為了幫助您抓取，我們直接印出環境資訊
    print("--- 偵測群組 ID 模式已啟動 ---")
    print("請確保 Bot 已在目標群組中，並在群組傳送過訊息。")
    # 這裡加入一行偵測，如果您已經設定好 Webhook，GitHub Actions 會試圖讀取相關事件
    # 若您是剛加入，請觀察 Log 中的 Source 欄位
    print(f"環境變數檢查完成，請確認 Log 中是否有顯示群組 ID 資訊。")
    # --- 結束 ---

    # 2. 生成內容
    themes = ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"]
    chosen_theme = random.choice(themes)
    prompt = f"你是溫柔牧者。請針對主題「{chosen_theme}」，精選一段聖經經文分享。格式：【經文內容】(阿們。)；【經文章節】；【領受與感悟】。禁止贅字，內容完整禁止斷章。"

    res = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.8))
    payload = res.text.strip()

    # 3. 推送至群組 (請將下方的 'Cxxxxxxx' 替換為您在 Log 中抓到的 ID)
    # 若還沒抓到，請先暫時使用您的個人 User ID 測試
    target_id = 'Cxxxxxxxxx' # <--- 待您在 Log 抓到後，填入此處
    
    try:
        line_api.push_message(target_id, TextSendMessage(text=f'【每日靈修】\n\n{payload}'))
        print(f"訊息已成功發送至: {target_id}")
    except Exception as e:
        print(f"推播失敗，請檢查 ID 是否正確: {e}")

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
    with open(temp_file, "w",
