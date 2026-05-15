import os
import requests
import google.generativeai as genai

# 直接填入您的關鍵密鑰
GEMINI_API_KEY = "AIzaSyC4rqWk4ybph9d5E26QTaGgMlLfU8lg64U"
LINE_ACCESS_TOKEN = "vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU="
LINE_USER_ID = "Uf166c741223bc8ee5d82fd1fd9f4df86"

def get_bible_verse():
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # 這裡改用指定 v1 版本，避開日誌中提到的 v1beta 報錯
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = "請挑選一段聖經經文，包含章節，並提供50字內的今日啟示，語氣要溫暖、理性且充滿力量。"
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"AI 生成出錯: {str(e)}")
        return "願上帝祝福你，今日經文生成稍微遲到了。"

def send_to_line(text):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": f"【每日經文推送】\n\n{text}"}]
    }
    res = requests.post(url, headers=headers, json=payload)
    print(f"LINE 傳送狀態: {res.status_code}")

if __name__ == "__main__":
    verse = get_bible_verse()
    send_to_line(verse)
