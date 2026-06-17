from flask import Flask, request, abort
from linebot import WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot import LineBotApi
import os
import google.generativeai as genai
import logging

# 設定日誌記錄
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 初始化設定
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])
line_api = LineBotApi(os.environ['LINE_TOKEN'])
genai.configure(api_key=os.environ['GEMINI_API_KEY'])

# [優化] 全域載入模型，減少記憶體波動
model = genai.GenerativeModel('gemini-2.5-flash')

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent)
def handle_message(event):
    # 讀取環境變數中的目標群組 ID
    TARGET_ID = os.environ.get('TARGET_GROUP_ID')
    
    # --- [暴力偵測模式] ---
    if event.source.type == "group":
        print(f"!!! DEBUG_GROUP_ID_FOUND: {event.source.group_id} !!!", flush=True)
    else:
        print(f"!!! DEBUG_EVENT_SOURCE: {event.source.type} !!!", flush=True)
    
    # --- [門禁系統] ---
    # 若為群組訊息，且 ID 不匹配，則靜默退出
    if event.source.type == "group" and event.source.group_id != TARGET_ID:
        return 

    # 靈修功能
    if isinstance(event.message, TextMessage) and "靈修" in event.message.text:
        try:
            res = model.generate_content("請精選一段聖經經文分享。格式：【經文】；【章節】；【感悟】")
            line_api.reply_message(event.reply_token, TextSendMessage(text=res.text))
        except Exception as e:
            print(f"靈修生成失敗: {e}", flush=True)
            line_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 靈修內容暫時無法讀取。"))

if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5000)))
