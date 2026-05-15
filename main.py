import streamlit as st
import os
import google.generativeai as genai
from datetime import datetime
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 1. 頁面自適應與 UI 優化 ---
st.set_page_config(
    page_title="K.I.T.T. 聖經控制台",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 手機版 UI 強化 CSS
st.markdown("""
    <style>
    .block-container { padding: 1.5rem 1rem !important; }
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.5em;
        font-weight: bold;
    }
    .main-btn { background-color: #007AFF !important; color: white !important; }
    .custom-btn { background-color: #34C759 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 安全密鑰校準 ---
def get_config(key, fallback):
    try:
        return st.secrets[key]
    except:
        return fallback

GEMINI_API_KEY = get_config("GEMINI_API_KEY", "AIzaSyC4rqWk4ybph9d5E26QTaGgMlLfU8lg64U")
LINE_ACCESS_TOKEN = get_config("LINE_ACCESS_TOKEN", "vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU=")
LINE_USER_ID = get_config("LINE_USER_ID", "Uf166c741223bc8ee5d82fd1fd9f4df86")

# 初始化
try:
    line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    st.error(f"系統初始化失敗: {e}")

# --- 3. UI 介面佈局 ---
st.title("🛡️ 聖經任務控制台")

# 狀態列
with st.container():
    c1, c2 = st.columns(2)
    c1.metric("今日日期", datetime.now().strftime("%m/%d"))
    c2.metric("傳輸狀態", "Ready")

st.markdown("---")

# 需求 1：增加手動貼上經文並推送
st.subheader("✍️ 自定義經文任務")
custom_verse = st.text_area("在此輸入您想分享的經文或訊息：", placeholder="例如：約翰福音 3:16...", height=150)

if st.button("📤 執行自定義推送"):
    if custom_verse.strip() == "":
        st.warning("請先輸入內容再執行推送。")
    else:
        try:
            with st.spinner("正在執行加密通訊..."):
                line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【手動自選經文】\n\n{custom_verse}"))
                st.balloons()
                st.success("自定義內容已送達您的手機。")
        except Exception as e:
            st.error(f"推送失敗：{e}")

st.markdown("---")

# 原有功能：AI 自動生成推送
st.subheader("🤖 AI 智慧靈糧")
if st.button("✨ 啟動 AI 生成並推送"):
    try:
        with st.spinner("AI 正在為您挑選今日經文..."):
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = "請挑選一段充滿力量的聖經經文與啟示，語氣溫暖，限制在80字內。"
            response = model.generate_content(prompt)
            
            line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【AI 推送任務】\n\n{response.text}"))
            st.success("AI 經文已成功發送！")
    except Exception as e:
        st.error(f"AI 生成異常：{e}")

st.caption("系統版本: CL3-Elite-v4.0 (Custom Messaging Supported)")
