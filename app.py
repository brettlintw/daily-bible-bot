from flask import Flask, request, abort
from linebot import WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot import LineBotApi
import os
import google.generativeai as genai
import logging

# 設定日誌記錄，以便在 Render Logs 中清楚看到輸出
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # --- [盤查戰術] 監測真實群組 ID ---
    if event.source.type == "group":
        group_id = event.source.group_id
        logger.info(f">>> 目前群組真實 ID 為: {group_id} <<<")
    
    # 靈修功能
    if "靈修" in event.message.text:
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            res = model.generate_content("請精選一段聖經經文分享。格式：【經文】；【章節】；【感悟】")
            line_api.reply_message(event.reply_token, TextSendMessage(text=res.text))
        except Exception as e:
            logger.error(f"靈修生成失敗: {e}")
            line_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 靈修內容暫時無法讀取，請稍候再試。"))

if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5000)))
