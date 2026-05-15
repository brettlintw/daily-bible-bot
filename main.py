import streamlit as st
import google.generativeai as genai
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.exceptions import InvalidSignatureError

# --- 系統核心金鑰 (由 Brett 授權) ---
GEMINI_API_KEY = "AIzaSyC4rqWk4ybph9d5E26QTaGgMlLfU8lg64U"
LINE_ACCESS_TOKEN = "vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET = "b7fe1a5a121e809214d5b26a1b3502d3"
LINE_USER_ID = "Uf166c741223bc8ee5d82fd1fd9f4df86"

# 初始化
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
genai.configure(api_key=GEMINI_API_KEY)

# --- UI 介面 ---
st.set_page_config(page_title="聖經 AI 任務控制台", page_icon="🛡️")
st.title("🛡️ 聖經 AI 任務控制台")
st.write(f"歡迎回來，**Brett**。系統運作狀態：穩定。")

st.divider()

# 通訊狀態區
st.subheader("📡 通訊狀態")
st.info("Webhook URL: `https://brett-bible-bot.streamlit.app`")
st.warning("⚠️ 提醒：Streamlit 網頁不支援 LINE 後台的 Verify 功能，請直接傳 LINE 訊息測試。")

# 手動執行區
st.subheader("⚡ 執行即時指令")
if st.button("🚀 執行：手動推送今日經文"):
    with st.spinner("AI 引擎正在分析經文內容..."):
        try:
            # 修正：使用更穩定的模型識別碼
            model = genai.GenerativeModel(model_name='gemini-1.5-flash')
            prompt = "請挑選一段聖經經文並提供50字內的溫暖啟示，語氣保持專業、理性且充滿力量。"
            response = model.generate_content(prompt)
            
            # 發送訊息
            line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【手動觸發】\n\n{response.text}"))
            st.success("任務達成：經文已送達您的 LINE。")
            st.balloons()
        except Exception as e:
            # 捕捉錯誤並顯示
            st.error(f"系統偵測到異常：{str(e)}")

# --- Webhook 偵聽 (當 LINE 伺服器傳送資料時) ---
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    try:
        model = genai.GenerativeModel(model_name='gemini-1.5-flash')
        prompt = f"使用者心情：'{user_text}'。請以基督徒顧問角度，給予溫暖安慰並引用適合的聖經經文，限制100字內。"
        response = model.generate_content(prompt)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response.text))
    except Exception as e:
        print(f"Error: {e}")

st.divider()
st.caption("K.I.T.T. 系統 | 任務代碼：BIBLE-PRO-2026")
