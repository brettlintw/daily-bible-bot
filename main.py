import streamlit as st
import google.generativeai as genai
from datetime import datetime
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 1. 頁面配置與手機版優化 ---
st.set_page_config(
    page_title="聖經控制台",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 注入 CSS：確保一頁式版面不溢出，隱藏滾動條
st.markdown("""
    <style>
    .block-container {
        padding: 0.8rem 0.8rem !important;
        max-width: 100vw !important;
        overflow-x: hidden;
    }
    h1 { font-size: 1.6rem !important; margin-bottom: 0.5rem !important; }
    h3 { font-size: 1.1rem !important; margin-top: 0.5rem !important; }
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.2em;
        font-weight: bold;
        background-color: #007AFF;
        color: white;
    }
    .stTextArea>div>div>textarea { border-radius: 12px; font-size: 16px !important; }
    [data-testid="stHeader"], footer, #MainMenu { visibility: hidden; height: 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 安全密鑰讀取 ---
def get_config(key, fallback):
    try: return st.secrets[key]
    except: return fallback

GEMINI_API_KEY = get_config("GEMINI_API_KEY", "AIzaSyC4rqWk4ybph9d5E26QTaGgMlLfU8lg64U")
LINE_ACCESS_TOKEN = get_config("LINE_ACCESS_TOKEN", "vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU=")
LINE_USER_ID = get_config("LINE_USER_ID", "Uf166c741223bc8ee5d82fd1fd9f4df86")

# 初始化
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. UI 介面佈局 ---
st.title("🛡️ 聖經任務控制台")
st.caption(f"📅 {datetime.now().strftime('%Y/%m/%d')} | 🛰️ 連線安全 | v5.1")

# ✍️ 即時傳輸任務
st.subheader("✍️ 即時傳輸任務")
custom_text = st.text_area("自選內容：", placeholder="在此貼上經文...", height=100, label_visibility="collapsed")
if st.button("📤 執行手動推送"):
    if custom_text.strip():
        try:
            line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【手動推送】\n\n{custom_text}"))
            st.toast("✅ 已成功送達")
            st.balloons()
        except: st.error("連線異常")

st.markdown("---")

# 🤖 AI 智慧靈糧 (修復 404 路徑報錯)
st.subheader("🤖 AI 智慧推送")
if st.button("✨ 啟動 AI 生成並推送"):
    try:
        with st.spinner("系統生成中..."):
            # 修正：針對 404 錯誤，加上完整的 'models/' 前綴
            model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
            res = model.generate_content("挑選一段充滿力量的聖經經文並給予啟示，限制在80字內。")
            
            if res and res.text:
                line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【AI推送】\n\n{res.text}"))
                st.toast("✨ AI推送成功")
                st.success("任務已送出")
            else: st.error("內容生成異常")
    except Exception as e:
        st.error("AI 系統暫時無法連線")
        st.caption(f"Debug: {str(e)[:50]}")
