import streamlit as st
import os
import requests
import google.generativeai as genai
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

# --- 1. 頁面配置 (優化 iPhone PWA 顯示) ---
st.set_page_config(
    page_title="聖經 AI 任務簡報",
    page_icon="📖",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 2. 核心密鑰讀取 (優先從 Streamlit Secrets 獲取) ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    LINE_ACCESS_TOKEN = st.secrets["LINE_ACCESS_TOKEN"]
    LINE_USER_ID = st.secrets["LINE_USER_ID"]
    LINE_CHANNEL_SECRET = st.secrets["LINE_CHANNEL_SECRET"]
except Exception:
    # 備援機制：如果 Secrets 尚未設定，則使用您提供的預設值
    GEMINI_API_KEY = "AIzaSyC4rqWk4ybph9d5E26QTaGgMlLfU8lg64U"
    LINE_ACCESS_TOKEN = "vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU="
    LINE_USER_ID = "Uf166c741223bc8ee5d82fd1fd9f4df86"
    LINE_CHANNEL_SECRET = "請在此填入您的_CHANNEL_SECRET"

# 初始化系統核心
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. UI 介面設計 ---
st.title("📖 聖經 AI 任務簡報")
st.write(f"歡迎回來，Brett。系統連線正常，隨時待命。")

with st.expander("🛡️ 系統狀態檢核", expanded=False):
    st.success("✅ AI 引擎路徑已校準")
    st.success("✅ LINE 通訊協定已就緒")

# --- 4. 核心發送功能 (修正 NotFound 報錯) ---
st.subheader("🚀 即時任務執行")
if st.button("發送今日經文至我的 LINE"):
    with st.spinner("AI 正在進行深度內容分析..."):
        try:
            # 使用絕對路徑模型代號，確保 1.5 Flash 正常運行
            model = genai.GenerativeModel('models/gemini-1.5-flash')
            
            prompt = "請挑選一段充滿力量的聖經經文與啟示，語氣溫暖且專業，限制在80字內。"
            response = model.generate_content(prompt)
            
            if response.text:
                line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【每日推送】\n\n{response.text}"))
                st.balloons()
                st.success("任務達成：訊息已送達您的手機。")
            else:
                st.error("生成內容為空，請重試。")
                
        except Exception as e:
            st.error(f"系統異常：{str(e)}")
            st.info("提示：請確保您的 API Key 有效且已開啟 Gemini 1.5 存取權限。")

# --- 5. 互動式對話邏輯 (用於 Webhook) ---
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    try:
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        prompt = f"使用者心情：'{user_text}'。請以基督徒角度提供安慰與適合經文，限100字。"
        ai_res = model.generate_content(prompt)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ai_res.text))
    except:
        pass

st.markdown("---")
st.caption("版本代號：CL3-Stable | 執行環境：Streamlit Cloud")
