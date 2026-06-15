from flask import Flask, request, abort
from linebot import WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import google.generativeai as genai

app = Flask(__name__)
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])
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
    if "靈修" in event.message.text:
        model = genai.GenerativeModel('gemini-2.5-flash')
        res = model.generate_content("請精選一段聖經經文分享。格式：【經文】；【章節】；【感悟】")
        from linebot import LineBotApi
        line_api = LineBotApi(os.environ['LINE_TOKEN'])
        line_api.reply_message(event.reply_token, TextSendMessage(text=res.text))

if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5000)))