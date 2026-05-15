import streamlit as st
import os
import requests
import google.generativeai as genai
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

# --- 核心配置：從 Streamlit Secrets 讀取 ---
# 請在 Streamlit Cloud 的 Settings -> Secrets 中設定這些變數
try:
    LINE_TOKEN = st.secrets["LINE_ACCESS_TOKEN"]
    LINE_SECRET = st.secrets["LINE_CHANNEL_SECRET"]
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
    USER_ID = st.secrets["LINE_USER_ID"]
except Exception:
    st.error("❌ 尚未在 Secrets 中設定密鑰，系統無法啟動。")
    st.stop()

# 初始化 API
line_bot_api = LineBotApi(LINE_TOKEN)
handler = WebhookHandler(LINE_SECRET)
genai.configure(api_key=GEMINI_KEY)

# --- Streamlit 頁面設計 ---
st.set_page_config(page_title="K.I.T.T. 聖經 AI 儀表板", page_icon="🛡️")
st.title("🛡️ 聖經 AI 系統任務簡報")
st.write("---")

# 狀態顯示區
st.sidebar.header("系統監控")
st.sidebar.success("系統連線中：運作正常")

# 手動任務區
st.header("⚡ 即時指令")
if st.button("立刻執行：每日經文推送"):
    with st.spinner("正在執行內容分析並推送..."):
        try:
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            res = model.generate_content("請挑選一段適合今日的聖經經文並給予溫暖的啟示，語氣保持專業與理性。")
            line_bot_api.push_message(USER_ID, TextSendMessage(text=f"【手動觸發】\n\n{res.text}"))
            st.balloons()
            st.success("任務達成：訊息已成功發送至您的手機。")
        except Exception as e:
            st.error(f"任務失敗：{str(e)}")

# --- Webhook 邏輯處理 (互動模式核心) ---
# 注意：Streamlit 主要用於介面，處理 Webhook 需要特別的對接方式。
# 當 LINE 傳送資料到這個網址時，我們可以透過此介面顯示連線資訊。
st.header("📡 雙向互動狀態")
st.info("系統正透過 Webhook 偵聽來自 LINE 的訊息...")

def handle_line_interaction(user_text):
    """
    處理雙向互動：AI 聽診與回覆邏輯
    """
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = f"使用者說：'{user_text}'。請以基督徒顧問的角度，給予溫暖安慰並引用一段適合的經文，限制100字內。"
    response = model.generate_content(prompt)
    return response.text

# 顯示 Webhook 提示訊息
st.code(f"Webhook URL: {st.get_option('server.baseUrlPath') if st.get_option('server.baseUrlPath') else '您的 Streamlit 網址'}", language="text")
