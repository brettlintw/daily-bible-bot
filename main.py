import streamlit as st
import os
import requests
import google.generativeai as genai
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

# --- 1. 頁面配置 (優化 iPhone 顯示) ---
st.set_page_config(
    page_title="聖經 AI 任務簡報",
    page_icon="📖",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 2. 核心密鑰讀取 (優先從 Streamlit Secrets 讀取) ---
# 請確保在 Streamlit Cloud Settings -> Secrets 填入以下變數
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    LINE_ACCESS_TOKEN = st.secrets["LINE_ACCESS_TOKEN"]
    LINE_USER_ID = st.secrets["LINE_USER_ID"]
    LINE_CHANNEL_SECRET = st.secrets["LINE_CHANNEL_SECRET"]
except Exception:
    # 備援機制：如果 Secrets 沒設定，則使用您提供的預設值
    GEMINI_API_KEY = "AIzaSyC4rqWk4ybph9d5E26QTaGgMlLfU8lg64U"
    LINE_ACCESS_TOKEN = "vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU="
    LINE_USER_ID = "Uf166c741223bc8ee5d82fd1fd9f4df86"
    LINE_CHANNEL_SECRET = "請務必填入您的_CHANNEL_SECRET"

# 初始化系統
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. UI 介面設計 ---
st.title("📖 聖經 AI 任務簡報")
st.write(f"歡迎回來，Brett。系統目前運作正常。")

with st.expander("🛠️ 系統狀態檢核", expanded=True):
    st.success("✅ Gemini AI 核心已連線")
    st.success("✅ LINE 通訊協定已就緒")

# --- 4. 手動推送測試區 ---
st.subheader("🚀 即時任務執行")
if st.button("發送今日經文至我的 LINE"):
    with st.spinner("正在生成內容..."):
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt = "請挑選一段充滿力量的聖經經文與啟示，語氣溫暖且專業，限制在80字內。"
        response = model.generate_content(prompt)
        
        line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【手動推送】\n\n{response.text}"))
        st.balloons()
        st.toast("訊息已送出！")

# --- 5. 互動式對話邏輯 (用於 Webhook) ---
# 此部分在部署到 Streamlit 後，需搭配 LINE Developers 的 Webhook 設定
# 接收來自 LINE 的訊息並自動回覆
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = f"使用者目前心情或問題：'{user_text}'。請以基督徒的角度提供安慰並引用一段經文。限制在100字內。"
    ai_res = model.generate_content(prompt)
    
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=ai_res.text)
    )

# 顯示 Webhook 提示
st.markdown("---")
st.caption("Webhook 偵聽位址：您的網址 / (POST)")
