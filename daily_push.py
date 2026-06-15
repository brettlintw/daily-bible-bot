import os
from linebot import LineBotApi
from linebot.models import TextSendMessage

# 初始化 API
line_api = LineBotApi(os.environ['LINE_TOKEN'])

def fetch_and_log_group_id():
    # 這是最後的戰術：
    # 我們不依賴 Webhook 監聽，我們直接在群組發一個測試訊息
    # 這裡我們預設您已經知道該群組的成員 UserID
    # 機器人只要在該群組內，我們可以透過 API 獲取該群組的詳細資訊
    
    # 【指令】請將此處填入您的「個人 User ID」
    # 我會直接推播測試訊息到該群組，確認群組 ID
    target_id = "C_YOUR_GROUP_ID_TO_TEST" 
    
    try:
        # 發送一個測試訊息到群組
        line_api.push_message(target_id, TextSendMessage(text="[系統測試] 正在偵測此群組 ID..."))
        print(f"✅ 已嘗試發送測試訊息至: {target_id}")
    except Exception as e:
        print(f"❌ 無法發送: {str(e)}")

if __name__ == "__main__":
    fetch_and_log_group_id()
