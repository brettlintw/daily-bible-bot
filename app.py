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

def build_quick_reply(event):
    buttons = [
        QuickReplyButton(action=MessageAction(label="查歷史", text="歷史 5")),
        QuickReplyButton(action=MessageAction(label="下載", text="下載")),
    ]
    if is_admin(event):
        buttons.insert(0, QuickReplyButton(action=MessageAction(label="推播", text="推播")))
    return QuickReply(items=buttons)


@handler.add(MessageEvent)
def handle_message(event):
    TARGET_ID = os.environ.get('TARGET_GROUP_ID')

    if event.source.type == "group":
        captured_id = event.source.group_id
        with open(bible_core.ID_FILE, "w") as f:
            f.write(captured_id)

    if event.source.type == "group" and event.source.group_id != TARGET_ID:
        return

    if not isinstance(event.message, TextMessage):
        return

    text = event.message.text
    command, arg = parse_command(text)

    if command == "whoami":
        line_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"你的 User ID 是：\n{getattr(event.source, 'user_id', '無法取得')}")
        )
        return

    if command == "menu":
        line_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請選擇功能：", quick_reply=build_quick_reply(event))
        )
        return

    if command == "history_error":
        line_api.reply_message(
            event.reply_token,
            TextSendMessage(text="⚠️ 格式錯誤，請用「歷史 5」這種格式（數字需為正整數）")
        )
        return

    if command == "history":
        try:
            items = bible_core.load_history()[:arg]
            if not items:
                reply_text = "目前還沒有歷史紀錄。"
            else:
                reply_text = "\n\n".join(
                    f"{h.get('date')} | {h.get('category')}\n{h.get('content')}" for h in items
                )
            line_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        except Exception as e:
            logger.error(f"查歷史失敗: {e}")
            line_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 暫時無法處理，稍後再試"))
        return

    if command == "download":
        line_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"完整歷史備份：\n{get_export_url()}")
        )
        return

    if command in ("push", "theme"):
        if not is_admin(event):
            line_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 這個指令你沒有權限使用"))
            return
        try:
            theme = arg if command == "theme" else None
            payload, chosen_theme = bible_core.generate_verse(
                os.environ['GEMINI_API_KEY'], theme=theme
            )
            bible_core.send_line_message(os.environ['LINE_TOKEN'], TARGET_ID, f'【每日靈修】\n\n{payload}')
            bible_core.record_entry(payload, f"指令-{chosen_theme}")
            line_api.reply_message(event.reply_token, TextSendMessage(text="✅ 已推播"))
        except Exception as e:
            logger.error(f"指令推播失敗: {e}")
            line_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 暫時無法處理，稍後再試"))
        return

    if "靈修" in text:
        try:
            payload, _ = bible_core.generate_verse(os.environ['GEMINI_API_KEY'])
            line_api.reply_message(event.reply_token, TextSendMessage(text=payload))
        except Exception as e:
            logger.error(f"靈修生成失敗: {e}")
            line_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 靈修內容暫時無法讀取。"))

if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5000)))
