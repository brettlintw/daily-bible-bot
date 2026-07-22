from flask import Flask, request, abort
from linebot import WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    QuickReply, QuickReplyButton, MessageAction,
)
from linebot import LineBotApi
import os
import logging

import bible_core
from command_parser import parse_command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 初始化設定
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])
line_api = LineBotApi(os.environ['LINE_TOKEN'])

# 讀取環境變數中的模型名稱
model_name = os.environ.get('GEMINI_MODEL_NAME', 'models/gemini-flash-latest')

# 有權限使用 推播/主題 指令的 LINE User ID（在 Render 環境變數設定）
ADMIN_USER_ID = os.environ.get('ADMIN_USER_ID', '').strip()


def is_admin(event):
    user_id = getattr(event.source, "user_id", None)
    return bool(ADMIN_USER_ID) and user_id == ADMIN_USER_ID

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


def get_export_url():
    base = os.environ.get('RENDER_EXTERNAL_URL', '').strip()
    if not base:
        base = f"http://localhost:{os.environ.get('PORT', 5000)}"
    return base.rstrip('/') + "/export"


@app.route("/export")
def export_history():
    data = bible_core.load_history()
    return bible_core.generate_html_backup(data)

@handler.add(MessageEvent)
def handle_message(event):
    TARGET_ID = os.environ.get('TARGET_GROUP_ID')
    
    if event.source.type == "group":
        captured_id = event.source.group_id
        with open("latest_group_id.txt", "w") as f:
            f.write(captured_id)
    
    if event.source.type == "group" and event.source.group_id != TARGET_ID:
        return 

    if isinstance(event.message, TextMessage) and "靈修" in event.message.text:
        try:
            res = model.generate_content("請精選一段聖經經文分享。格式：【經文】；【章節】；【感悟】")
            line_api.reply_message(event.reply_token, TextSendMessage(text=res.text))
        except Exception as e:
            logger.error(f"靈修生成失敗: {e}")
            line_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 靈修內容暫時無法讀取。"))

if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5000)))
