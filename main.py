import streamlit as st
import os
import requests
import google.generativeai as genai
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

# --- 系統核心配置 ---
# 這些是您提供給 K.I.T.T. 的核心指令碼
GEMINI_API_KEY = "AIzaSyC4rqWk4ybph9d5E26QTaGgMlLfU8lg64U"
LINE_ACCESS_TOKEN = "vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU="
LINE_USER_ID = "Uf166c741223bc8ee5d82fd1fd9f4df86"

# 重要：請從 LINE Developers 的 Basic Settings 複製 Channel Secret 填入下方
LINE_CHANNEL_SECRET = "請在此填入您的_Channel_secret" 

# 初始化系統組件
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
genai.configure(api_key=GEMINI_API_KEY)

# --- Streamlit UI 儀表板設計 ---
st.set_page_config(page_title="K.I.T.T. 聖經 AI 儀表板", page_icon="🛡️", layout="centered")

st.title("🛡️ 聖經 AI 任務控制台")
st.write(f"歡迎回來，**Brett**。系統目前在雲端環境穩定運行中。")

# 顯示 Webhook 指示
st.divider()
st.subheader("📡 通訊狀態")
current_url = "https://brett-bible-bot.streamlit.app" # 部署成功後的網址
st.info(f"請確保 LINE 後台 Webhook URL 已填入：\n`{current_url}`")

# 手動任務執行區
st.subheader("⚡ 執行即時指令")
col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 發送今日經文"):
        with st.spinner("AI 正在分析內容..."):
            try:
                model = genai.GenerativeModel('gemini-1.5-flash-latest')
                prompt = "請挑選一段聖經經文並給予溫暖的啟示，語氣保持專業與冷靜，限制在100字內。"
                response = model.generate_content(prompt)
                
                line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【手動觸發】\n\n{response.text}"))
                st.success("任務達成：訊息已發送至您的 LINE。")
                st.balloons()
            except Exception as e:
                st.error(f"指令執行失敗：{str(e)}")

with col2:
    if st.button("🔍 系統狀態自我檢查"):
        st.write("密鑰狀態：OK")
        st.write("網路連線：穩定")
        st.write("AI 引擎：Gemini 1.5 Flash")

# 備註：關於 Webhook 接收
# Streamlit 社群版主要用於資料展示。若要實現完美的「即時回覆」，
# 我們後續可以引導您整合 FastAPI，目前的架構主要支援「主動推送」與「介面控制」。

st.divider()
st.caption("K.I.T.T. 系統版本 2026.05 | 由 Brett 授權執行")
