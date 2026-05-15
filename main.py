import streamlit as st
import os
import requests
import google.generativeai as genai
from datetime import datetime
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# --- 1. 頁面自適應配置 ---
st.set_page_config(
    page_title="聖經 AI 任務簡報",
    page_icon="📖",
    layout="centered", 
    initial_sidebar_state="collapsed"
)

# --- 2. 注入手機版自適應 CSS ---
st.markdown("""
    <style>
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }
    h1 {
        font-size: 1.8rem !important;
        line-height: 1.2 !important;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        margin-top: 10px;
    }
    .stMetric, .stAlert, .stExpander {
        border-radius: 15px !important;
    }
    [data-testid="stHeader"] {
        background: rgba(0,0,0,0);
        height: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 核心密鑰讀取 ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    LINE_ACCESS_TOKEN = st.secrets["LINE_ACCESS_TOKEN"]
    LINE_USER_ID = st.secrets["LINE_USER_ID"]
    LINE_CHANNEL_SECRET = st.secrets["LINE_CHANNEL_SECRET"]
except Exception:
    GEMINI_API_KEY = "AIzaSyC4rqWk4ybph9d5E26QTaGgMlLfU8lg64U"
    LINE_ACCESS_TOKEN = "vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU="
    LINE_USER_ID = "Uf166c741223bc8ee5d82fd1fd9f4df86"
    LINE_CHANNEL_SECRET = "您的_CHANNEL_SECRET"

# 初始化系統
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# --- 4. 行動端 UI 佈局 ---
st.title("🛡️ 聖經 AI 任務簡報")

with st.container():
    col1, col2 = st.columns([1, 1])
    with col1:
        st.write(f"📅 **今日日期**")
        st.subheader(datetime.now().strftime("%Y/%m/%d"))
    with col2:
        st.write(f"🌤️ **目前天氣**")
        st.subheader("晴朗, 26°C")

st.markdown("---")

with st.expander("⏰ 推送時間排程管理", expanded=False):
    st.info("目前設定：每日 06:30 (台灣時間)")
    if st.button("修改推送時間"):
        st.warning("排程功能連線中...")

st.subheader("🚀 手動發送任務")
if st.button("立刻發送一段暖心經文"):
    with st.spinner("AI 正在準備靈糧..."):
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt = "請挑選一段充滿力量的聖經經文與啟示，語氣溫暖，限制在80字內。"
        response = model.generate_content(prompt)
        
        line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【手動推送】\n\n{response.text}"))
        st.success("任務達成！請查看您的 LINE。")
        st.balloons()

st.caption("系統版本: CL3-Elite-v3.1 (Mobile Optimized)")
