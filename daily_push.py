import os
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage

def run_daily_push():
    # 1. 初始化
    genai.configure(api_key=os.environ['GEMINI_API_KEY'])
    line_api = LineBotApi(os.environ['LINE_TOKEN'])
    
    # 2. 強制除錯偵測 (刻意輸入錯誤的 ID 以獲取 LINE 伺服器回應中的關聯資料)
    target_id = 'C_FORCE_ERROR_GET_ID' 
    
    try:
        print(f"--- 開始偵測 API 關聯 ID ---")
        line_api.push_message(target_id, TextSendMessage(text='【除錯偵測 ID】'))
    except Exception as e:
        # 錯誤訊息 e 中會包含 LINE 伺服器對該帳號的錯誤說明，通常會列出綁定的清單
        print(f"--- 捕獲到 API 錯誤訊息 (請將此內容全部貼給我) ---")
        print(f"{str(e)}") 
        print(f"--- 訊息結束 ---")

if __name__ == "__main__":
    run_daily_push()
