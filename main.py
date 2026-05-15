import streamlit as st
import google.generativeai as genai
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# --- 安全讀取配置 ---
try:
    # 這裡會從 Streamlit 的 Settings -> Secrets 讀取
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    LINE_ACCESS_TOKEN = st.secrets["LINE_ACCESS_TOKEN"]
    LINE_CHANNEL_SECRET = st.secrets["LINE_CHANNEL_SECRET"]
    LINE_USER_ID = st.secrets["LINE_USER_ID"]
except Exception:
    st.error("❌ 系統偵測到 Secrets 配置遺失，請至 Streamlit 後台設定。")
    st.stop()

# 初始化
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

st.title("🛡️ 聖經 AI 安全控制台")
st.write(f"歡迎回來，**Brett**。")

if st.button("🚀 執行：安全推送任務"):
    try:
        # 使用最新的穩定模型
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("請提供一段充滿正能量的聖經經文。")
        
        line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=response.text))
        st.success("任務成功：新 API Key 運作正常！")
        st.balloons()
    except Exception as e:
        st.error(f"系統異常：{str(e)}")
