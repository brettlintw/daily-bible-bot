import os
import requests
import google.generativeai as genai

# 1. 檢查密鑰 (環境變數)
GEMINI_KEY = os.getenv('AIzaSyC4rqWk4ybph9d5E26QTaGgMlLfU8lg64U')
LINE_TOKEN = os.getenv('vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU=')
USER_ID = os.getenv('Uf166c741223bc8ee5d82fd1fd9f4df86')

print(f"DEBUG: GEMINI_KEY 存在? {'是' if GEMINI_KEY else '否'}")
print(f"DEBUG: LINE_TOKEN 存在? {'是' if LINE_TOKEN else '否'}")
print(f"DEBUG: USER_ID 存在? {'是' if USER_ID else '否'}")

def test_run():
    if not all([GEMINI_KEY, LINE_TOKEN, USER_ID]):
        print("!!! 錯誤: 某個 Secrets 變數遺失了，請檢查 GitHub Settings !!!")
        return

    # 測試 AI 生成
    try:
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("測試經文生成")
        content = response.text
        print("DEBUG: AI 生成內容成功")
    except Exception as e:
        print(f"!!! AI 報錯: {str(e)}")
        return

    # 測試 LINE 發送
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}"
    }
    payload = {
        "to": USER_ID,
        "messages": [{"type": "text", "text": content}]
    }
    
    res = requests.post(url, headers=headers, json=payload)
    print(f"DEBUG: LINE 狀態碼: {res.status_code}")
    print(f"DEBUG: LINE 回傳訊息: {res.text}")

if __name__ == "__main__":
    test_run()
