from linebot.models import MessageEvent, TextMessage, TextSendMessage

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 這是最強制的獲取 ID 方式
    # 如果 event.source 包含 group_id，直接回覆給您
    source_id = "未知"
    if event.source.type == "group":
        source_id = event.source.group_id
    elif event.source.type == "room":
        source_id = event.source.room_id
        
    line_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"偵測到 ID: {source_id}")
    )
