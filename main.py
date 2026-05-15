import os
import requests
import google.generativeai as genai

# 核心參數配置：由 Brett 提供
GEMINI_API_KEY = "AIzaSyC4rqWk4ybph9d5E26QTaGgMlLfU8lg64U"
LINE_ACCESS_TOKEN = "vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU="
LINE_USER_ID = "Uf166c741223bc8ee5d82fd1fd9f4df86"

def get_daily_verse():
    """
    調用 Gemini AI 獲取每日聖經經文與解析
    """
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # 使用最新穩定版模型
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        prompt = "請挑選一段聖經經文（包含章節），並提供50字內的今日啟示，語氣要溫暖、理性且充滿力量。請直接輸出內容。"
        
        response = model.generate_content(prompt)
        if response.text:
            return response.text
        return "今日靈糧正在準備中，請稍候再試。"
    except Exception as e:
        return f"AI 引擎暫時連線異常: {str(e)}"

def send_to_line(message_text):
    """
    透過 LINE Messaging API 將訊息推送到 Brett 的手機
    """
    url = "https://api.line.me/v2/bot/message/push"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    
    payload = {
        "to": LINE_USER_ID,
        "messages": [
            {
                "type": "text",
                "text": f"【每日聖經經文推送】\n\n{message_text}"
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            print("任務達成：訊息已成功送達您的手機。")
        else:
            print(f"發送失敗，狀態碼：{response.status_code}")
            print(f"錯誤訊息：{response.text}")
    except Exception as e:
        print(f"通訊系統發生異常：{str(e)}")

if __name__ == "__main__":
    # 啟動任務程序
    print("正在執行內容分析...")
    verse_content = get_daily_verse()
    
    print("正在執行推送任務...")
    send_to_line(verse_content)
