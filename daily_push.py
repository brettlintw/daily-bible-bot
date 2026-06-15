import os
from linebot import LineBotApi
# 補上這行匯入，修復剛剛的錯誤
from linebot.models import TextSendMessage 

line_api = LineBotApi(os.environ['LINE_TOKEN'])

def fetch_group_id():
    print("--- 開始偵測群組資訊 ---")
    # 請將下方 C_TEST_ID_12345 替換為該群組的「邀請連結網址」或您猜測的 ID
    # 這裡我們換一個更穩定的釣魚方式：
    # 如果您有任何「懷疑」是該群組的 ID，請填入這裡，它會嘗試發送
    target_id = "C_YOUR_SUSPECTED_ID" 
    
    try:
        line_api.push_message(target_id, TextSendMessage(text="[測試] 若收到此訊息，代表 ID 正確。"))
        print(f"✅ 釣魚成功！目標 ID: {target_id}")
    except Exception as e:
        # 錯誤訊息中通常會包含伺服器回傳的 ID 資訊
        print(f"釣魚結果: {e}")

if __name__ == "__main__":
    fetch_group_id()
