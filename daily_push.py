import os
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 1. 必須先宣告 handler 物件，否則會報錯
handler = WebhookHandler(os.environ.get('LINE_CHANNEL_SECRET', 'DEFAULT_SECRET'))
line_api = LineBotApi(os.environ.get('LINE_TOKEN', 'DEFAULT_TOKEN'))

# 2. 現在 handler 已定義，這段裝飾器就不會再崩潰了
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 這是偵測 ID 的邏輯
    source_id = "非群組"
    if event.source.type == "group":
        source_id = event.source.group_id
    elif event.source.type == "room":
        source_id = event.source.room_id
        
    line_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"偵測到 ID: {source_id}")
    )

if __name__ == "__main__":
    print("偵測程式初始化完成。請在 LINE 群組發送訊息測試。")
