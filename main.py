import streamlit as st
import os
import requests
import google.generativeai as genai
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

# --- 核心密鑰配置 ---
GEMINI_API_KEY = "AIzaSyC4rqWk4ybph9d5E26QTaGgMlLfU8lg64U"
LINE_ACCESS_TOKEN = "vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU="
LINE_USER_ID = "Uf166c741223bc8ee5d82fd1fd9f4df86"
# 注意：Channel Secret 需在 LINE Basic Settings 取得，請填入下方引號中
LINE_CHANNEL_SECRET = "您的_CHANNEL_SECRET_在此" 

# 初始化 API
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
genai.configure(api_key=GEMINI_API_KEY)

# --- Streamlit 介面設計 ---
st.set_page_config(page_title="K.I.T.T. 聖經機器人控制台", page_icon="🛡️")
st.title("🛡️ 聖經機器人任務簡報")
st.status("系統核心已啟動，待命中...", state="running")

# 模擬測試區
st.sidebar.header("系統測試")
test_msg = st.sidebar.text_input("輸入心情測試 AI 回應：")
if st.sidebar.button("手動測試生成"):
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    res = model.generate_content(f"我現在心情：{test_msg}，請給我一段安慰的聖經經文。")
    st.sidebar.write(res.text)

# --- Webhook 邏輯 (處理 LINE 傳來的訊息) ---
# Streamlit 本身不直接支援 POST Webhook，這部分是為了讓外部平台呼叫時不噴錯
st.write("---")
st.info("此網頁目前作為 Webhook 接收端，請將此網頁網址填入 LINE Developers 後台。")

# 這裡我們定義一個簡單的處理函數
def handle_interaction(user_text, reply_token):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt = f"使用者說：'{user_text}'。請根據他的心情，提供一段溫暖的聖經經文與50字內的安慰。語氣要像專業的顧問。"
        response = model.generate_content(prompt)
        line_bot_api.reply_message(reply_token, TextSendMessage(text=response.text))
    except Exception as e:
        st.error(f"AI 回應失敗: {e}")

# 注意：在 Streamlit 實現真正的 Webhook 接收通常需要配合 streamlit-fastapi 或 flask。
# 如果您部署到 Streamlit Cloud，建議將此檔案作為展示介面，
# 而真正的互動功能通常會部署在 Render 或 Heroku 上。
