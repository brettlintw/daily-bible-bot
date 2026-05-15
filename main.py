import streamlit as st
import google.generativeai as genai
from datetime import datetime
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 1. 頁面極簡化配置 ---
st.set_page_config(
    page_title="聖經控制台",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 注入 CSS：極度壓縮間距，確保一頁顯示
st.markdown("""
    <style>
    /* 移除所有多餘間距 */
    .block-container {
        padding: 0.5rem 0.8rem !important;
        max-width: 100vw !important;
    }
    /* 縮小標題字體 */
    h1 { font-size: 1.4rem !important; margin-bottom: 0.2rem !important; }
    h3 { font-size: 1rem !important; margin-top: 0.5rem !important; margin-bottom: 0.3rem !important; }
    
    /* 按鈕緊湊化 */
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 2.8rem;
        font-weight: 600;
        margin-top: 2px;
    }
    
    /* 輸入框緊湊化 */
    .stTextArea>div>div>textarea {
        border-radius: 10px;
        font-size: 15px !important;
        height: 80px !important;
    }

    /* 隱藏裝飾元素 */
    [data-testid="stHeader"], footer, #MainMenu { visibility: hidden; height: 0; }
    div[data-testid="stExpander"] { margin-top: 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心密鑰讀取 ---
def get_config(key, fallback):
    try: return st.secrets[key]
    except: return fallback

GEMINI_API_KEY = get_config("GEMINI_API_KEY", "AIzaSyC4rqWk4ybph9d5E26QTaGgMlLfU8lg64U")
LINE_ACCESS_TOKEN = get_config("LINE_ACCESS_TOKEN", "vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU=")
LINE_USER_ID = get_config("LINE_USER_ID", "Uf166c741223bc8ee5d82fd1fd9f4df86")

# 初始化
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. 一頁式介面佈局 ---
st.title("🛡️ 聖經任務控制台")

# 狀態資訊列 (一行搞定)
st.caption(f"📅 {datetime.now().strftime('%m/%d')} | 🛰️ 連線安全 | v7.2")

# ✍️ 即時傳輸任務 (縮小區域)
st.subheader("✍️ 即時傳輸")
custom_verse = st.text_area("自選內容：", placeholder="貼上經文...", label_visibility="collapsed")

if st.button("📤 執行手動推送"):
    if custom_verse.strip():
        try:
            line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【手動推送】\n\n{custom_verse}"))
            st.toast("✅ 已送達")
        except: st.error("連線中斷")

st.markdown("---")

# 🤖 AI 排程與生成 (整合區塊)
st.subheader("⏰ AI 排程與推送")
selected_time = st.selectbox("自動推送時間：", ["06:30", "07:00", "08:00", "09:00"], index=2, label_visibility="collapsed")

c1, c2 = st.columns(2)
with c1:
    if st.button("💾 確認設定"):
        st.toast(f"已設為 {selected_time}")
with c2:
    if st.button("✨ AI 測試"):
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            res = model.generate_content("挑選一段充滿力量的聖經經文與啟示，80字內。")
            line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【AI測試】\n\n{res.text}"))
            st.toast("✨ AI推送成功")
        except: st.error("AI異常")
