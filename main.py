import os
import requests
import google.generativeai as genai

# 從您設定的 Secrets 讀取密鑰
GEMINI_KEY = os.getenv('AIzaSyC4rqWk4ybph9d5E26QTaGgMlLfU8lg64U')
LINE_TOKEN = os.getenv('vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU=')
USER_ID = os.getenv('Uf166c741223bc8ee5d82fd1fd9f4df86')

def get_bible_verse():
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    # 您可以調整提示詞讓經文更符合當下的心情
    prompt = "請挑選一段聖經經文，並提供50字內的今日啟示，語氣要溫暖且充滿力量。"
    response = model.generate_content(prompt)
    return response.text

def send_line_message(text):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}"
    }
    payload = {
        "to": USER_ID,
        "messages": [{"type": "text", "text": text}]
    }
    response = requests.post(url, headers=headers, json=payload)
    print(f"LINE 傳送狀態: {response.status_code}")

if __name__ == "__main__":
    verse = get_bible_verse()
    send_line_message(verse)
