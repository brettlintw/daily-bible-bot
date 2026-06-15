import os
from linebot import LineBotApi

line_api = LineBotApi(os.environ['LINE_TOKEN'])

def fetch_group_id():
    print("--- 開始偵測群組資訊 ---")
    # 因為 API 不提供直接列出所有群組，我們透過 "推送" 的錯誤訊息來釣出 ID
    # 這裡我們嘗試推一個空訊息，看看會發生什麼
    try:
        # 這會失敗，但錯誤訊息通常會包含您正在嘗試操作的目標
        line_api.push_message('C_TEST_ID_12345', TextSendMessage(text="測試"))
    except Exception as e:
        # 我們直接把錯誤訊息印在 Log 裡
        print(f"釣魚結果: {e}")

if __name__ == "__main__":
    fetch_group_id()
