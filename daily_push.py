import os
import random
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage

def run_daily_push():
    # 1. 初始化
    genai.configure(api_key=os.environ['GEMINI_API_KEY'])
    model = genai.GenerativeModel('gemini-2.5-flash')
    line_api = LineBotApi(os.environ['LINE_TOKEN'])
    
    # 2. 生成內容 (測試用)
    prompt = "請簡短分享一段聖經經文與感悟。"
    payload = model.generate_content(prompt).text.strip()
    
    # 3. 強制除錯偵測 (此處填入錯誤 ID 以觸發 API 報錯並獲取關聯群組)
    # 當您推送到 GitHub 並執行 Action 後，查看 Log 裡的紅色錯誤訊息
    target_id = 'C_DEBUG_FORCE_ERROR_GET_ID' 
    
    try:
        print(f"--- 開始偵測 API 關聯 ID ---")
        line_api.push_message(target_id, TextSendMessage(text=f'【除錯測試】\n\n{payload}'))
    except Exception as e:
        # 錯誤訊息 e 通常會包含該帳號下綁定的群組 ID 資訊
        print(f"--- 捕獲到 API 錯誤訊息 (請複製此內容給我) ---")
        print(f"{str(e)}") 
        print(f"--- 訊息結束 ---")

if __name__ == "__main__":
    run_daily_push()
