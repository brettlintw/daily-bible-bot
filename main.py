import streamlit as st
import google.generativeai as genai
from datetime import datetime
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 1. 頁面配置與手機優化 ---
st.set_page_config(
    page_title="K.I.T.T. 聖經控制台",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 手機版 UI 強化 CSS：鎖定寬度防止溢出
st.markdown("""
    <style>
    .block-container { padding: 1rem 0.8rem !important; max-width: 100vw !important; overflow-x: hidden; }
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.5em;
        font-weight: bold;
    }
    .stTextArea>div>div>textarea { border-radius: 12px; font-size: 16px !important; }
    [data-testid="stHeader"], footer, #MainMenu { visibility: hidden; height: 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 安全密鑰讀取 ---
def get_config(key, fallback):
    try:
        return st.secrets[key]
    except:
        return fallback

GEMINI_API_KEY = get_config("GEMINI_API_KEY", "AIzaSyC4rqWk4ybph9d5E26QTaGgMlLfU8lg64U")
LINE_ACCESS_TOKEN = get_config("LINE_ACCESS_TOKEN", "vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU=")
LINE_USER_ID = get_config("LINE_USER_ID", "Uf166c741223bc8ee5d82fd1fd9f4df86")

# 初始化
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. UI 介面佈局 ---
st.title("🛡️ 聖經任務控制台")
st.caption(f"📅 {datetime.now().strftime('%Y/%m/%d')} | 🛰️ 安全連線 | v4.1-Fixed")

st.markdown("---")

# ✍️ 自定義經文任務
st.subheader("✍️ 即時傳輸任務")
custom_verse = st.text_area("自選內容：", placeholder="在此輸入您想分享的經文或訊息...", height=100, label_visibility="collapsed")

if st.button("📤 執行手動推送"):
    if custom_verse.strip():
        try:
            line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【手動推送】\n\n{custom_verse}"))
            st.success("已成功送達")
            st.balloons()
        except Exception as e:
            st.error(f"推送失敗: {e}")

st.markdown("---")

# 🤖 AI 智慧靈糧 (參考 V4.1 成功版本修正模型路徑)
st.subheader("🤖 AI 智慧推送")
if st.button("✨ 啟動 AI 生成並推送"):
    try:
        with st.spinner("AI 正在搜尋經文..."):
            # 使用 V4.1 驗證過的最穩定模型路徑格式
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = "請幫我從聖經中挑選一段適合今日的經文並給予一段溫暖的啟示，總字數限制在80字內。"
            response = model.generate_content(prompt)
            
            if response and response.text:
                line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【AI推送任務】\n\n{response.text}"))
                st.success("AI 任務已送達")
                st.toast("✨ 生成成功")
            else:
                st.error("AI 內容生成異常")
    except Exception as e:
        st.error("AI 系統暫時無法連線")
        st.caption(f"Debug Info: {str(e)[:100]}")
