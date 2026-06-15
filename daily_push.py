import os
import json
import random
import subprocess
import shutil
from datetime import datetime, timezone, timedelta
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# --- 設定 ---
app = Flask(__name__)
DB_FILE = "bible_history.json"
TZ_TW = timezone(timedelta(hours=8))

# 從環境變數讀取 Token
line_api = LineBotApi(os.environ['LINE_TOKEN'])
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])

# --- 核心邏輯：Webhook 回應 (這會讓 Bot 在群組自報 ID) ---
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 獲取群組 ID (如果是群組的話)
    group_id = event.source.group_id if hasattr(event.source, 'group_id') else "非群組"
    # 當有人說話時，Bot 直接回傳該群組 ID
    line_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"偵測到 ID: {group_id}")
    )

# --- 靈修推播功能 (供 workflow_dispatch 呼叫) ---
def run_daily_push():
    import google.generativeai as genai
    genai.configure(api_key=os.environ['GEMINI_API_KEY'])
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"你是溫柔牧者。請精選一段聖經經文分享。格式：【經文內容】(阿們。)；【經文章節】；【領受與感悟】。"
    payload = model.generate_content(prompt).text.strip()
    
    # 請在抓到 ID 後，將此處改為您的真實 C 開頭 ID
    target_id = 'Uf166c741223bc8ee5d82fd1fd9f4df86'
    line_api.push_message(target_id, TextSendMessage(text=f'【每日靈修】\n\n{payload}'))
    print(f"推播完成至: {target_id}")

if __name__ == "__main__":
    # 這是為了讓您可以在本地端測試或部署在支援 Webhook 的平台上
    app.run(port=5000)
