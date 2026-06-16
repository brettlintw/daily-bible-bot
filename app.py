from flask import Flask, request, abort
from linebot import WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot import LineBotApi
import os
import google.generativeai as genai

app = Flask(__name__)

# 確保這些變數在 Render 的 Environment Variables 設定好
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])
line_api = LineBotApi(os.environ['LINE_TOKEN'])
genai.configure(api_key=os.environ['GEMINI_API_KEY'])

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
    # --- [暴力偵測模式] ---
    # 使用 print 並配合 flush=True 強制立即輸出至 Render Logs
    if event.source.type == "group":
        print(f"!!! DEBUG_GROUP_ID_FOUND: {event.source.group_id} !!!", flush=True)
    else:
        print(f"!!! DEBUG_EVENT_SOURCE: {event.source.type} !!!", flush=True)
    
    # 靈修功能
    if isinstance(event.message, TextMessage) and "靈修" in event.message.text:
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            res = model.generate_content("請精選一段聖經經文分享。格式：【經文】；【章節】；【感悟】")
            line_api.reply_message(event.reply_token, TextSendMessage(text=res.text))
        except Exception as e:
            print(f"靈修生成失敗: {e}", flush=True)
            line_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 靈修內容暫時無法讀取。"))

if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5000)))
