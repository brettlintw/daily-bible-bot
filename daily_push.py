import os
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

# 這裡初始化設定
line_api = LineBotApi(os.environ['LINE_TOKEN'])
handler = WebhookHandler(os.environ['LINE_CHANNEL_SECRET'])

def run_id_hunter(event):
    # 這是核心邏輯：偵測來源類型，如果是群組，直接抓取 ID
    source_id = "未知來源"
    if event.source.type == "group":
        source_id = event.source.group_id
    elif event.source.type == "room":
        source_id = event.source.room_id
    elif event.source.type == "user":
        source_id = event.source.user_id
        
    # 回覆 ID 給您
    line_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"偵測到 ID: {source_id}")
    )

# 模擬處理事件 (為了讓 GitHub Actions 跑得動，我們定義 handler)
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    run_id_hunter(event)

if __name__ == "__main__":
    print("ID 獵人模式啟動：請在群組發送任意訊息。")
