import streamlit as st
import google.generativeai as genai
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# --- 系統核心金鑰 ---
GEMINI_API_KEY = "AIzaSyC4rqWk4ybph9d5E26QTaGgMlLfU8lg64U"
LINE_ACCESS_TOKEN = "vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET = "b7fe1a5a121e809214d5b26a1b3502d3"
LINE_USER_ID = "Uf166c741223bc8ee5d82fd1fd9f4df86"

# 初始化
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 強制配置：確保不使用舊版的 v1beta 接口
genai.configure(api_key=GEMINI_API_KEY)

# --- UI 介面 ---
st.set_page_config(page_title="聖經 AI 任務控制台", page_icon="🛡️")
st.title("🛡️ 聖經 AI 任務控制台")
st.write(f"歡迎回來，**Brett**。系統巡檢中...")

st.divider()

# 手動執行區
st.subheader("⚡ 執行即時指令")
if st.button("🚀 執行：手動推送今日經文"):
    with st.spinner("AI 引擎通訊中..."):
        try:
            # 嘗試使用最基礎的模型路徑
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # 加入安全性過濾器設定，避免因為內容審查導致失敗
            response = model.generate_content(
                "請挑選一段聖經經文並提供50字內的啟示。",
                safety_settings=[
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                ]
            )
            
            if response and response.text:
                line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【每日靈糧】\n\n{response.text}"))
                st.success("任務達成：訊息已成功送達。")
                st.balloons()
            else:
                st.error("AI 回傳了空的結果，請檢查 API Key 是否有權限使用此模型。")
                
        except Exception as e:
            st.error(f"⚠️ 系統偵測到異常：{str(e)}")
            st.info("💡 解決建議：如果錯誤持續，請確認 Google AI Studio 中是否已啟用 Gemini 1.5 Flash。")

st.divider()
st.caption("K.I.T.T. 系統版本 2026.05 | 由 Brett 授權執行")
