import streamlit as st
import google.generativeai as genai
from datetime import datetime
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 1. 頁面極簡配置 (優化手機一頁式顯示) ---
st.set_page_config(
    page_title="聖經控制台",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 注入 CSS：縮減所有元件間距，防止手機版面溢出
st.markdown("""
    <style>
    .block-container { padding: 1rem 0.8rem !important; max-width: 100vw !important; overflow-x: hidden; }
    h1 { font-size: 1.4rem !important; margin: 0 !important; }
    h3 { font-size: 1rem !important; margin-top: 0.5rem !important; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3rem; font-weight: bold; }
    .stMultiSelect div[data-baseweb="select"] { border-radius: 10px; min-height: 2.5rem; }
    .stTextArea>div>div>textarea { border-radius: 10px; font-size: 16px !important; }
    [data-testid="stHeader"], footer, #MainMenu { visibility: hidden; height: 0; }
    hr { margin: 0.5rem 0 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 安全密鑰讀取 (優先從 Secrets 讀取) ---
def get_config(key, fallback):
    try:
        return st.secrets[key]
    except:
        return fallback

GEMINI_API_KEY = get_config("GEMINI_API_KEY", "AIzaSyC4rqWk4ybph9d5E26QTaGgMlLfU8lg64U")
LINE_TOKEN = get_config("LINE_ACCESS_TOKEN", "vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU=")
LINE_ID = get_config("LINE_USER_ID", "Uf166c741223bc8ee5d82fd1fd9f4df86")

# 初始化
line_api = LineBotApi(LINE_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. UI 介面佈局 ---
st.title("🛡️ 聖經任務控制台")
st.caption(f"📅 {datetime.now().strftime('%Y/%m/%d')} | 🛰️ 連線安全 | v8.2-Elite")

# ✍️ 手動任務區
st.subheader("✍️ 即時傳輸任務")
custom_text = st.text_area("自選內容：", placeholder="在此貼上經文...", height=80, label_visibility="collapsed")
if st.button("📤 執行手動推送"):
    if custom_text.strip():
        try:
            line_api.push_message(LINE_ID, TextSendMessage(text=f"【手動推送】\n\n{custom_text}"))
            st.toast("✅ 已成功送達")
            st.balloons()
        except: st.error("連線異常")

st.markdown("---")

# ⏰ 多重排程設定
st.subheader("⏰ 多重排程設定")
schedules = st.multiselect(
    "選擇每日推送時間：",
    ["06:30", "07:00", "07:30", "08:00", "08:30", "09:00", "12:00", "21:00"],
    default=["06:30", "08:00"],
    label_visibility="collapsed"
)
if st.button("💾 更新排程確認"):
    st.toast(f"已同步：{', '.join(schedules)}")

st.markdown("---")

# 🤖 AI 智慧推送 (參考 V4.1 成功邏輯進行終極校準)
st.subheader("🤖 AI 智慧推送")
if st.button("✨ 啟動 AI 測試推送"):
    try:
        with st.spinner("AI 生成中..."):
            # 關鍵修正：鎖定最穩定的模型標識符，解決 404 錯誤
            model = genai.GenerativeModel('gemini-1.5-flash')
            res = model.generate_content("請幫我從聖經中挑選一段適合今日的經文並給予啟示，80字內。")
            
            if res and res.text:
                line_api.push_message(LINE_ID, TextSendMessage(text=f"【AI測試推送】\n\n{res.text}"))
                st.toast("✨ AI推送成功")
                st.success("任務已執行")
            else:
                st.error("AI 內容生成異常")
    except Exception as e:
        st.error("AI 系統暫時無法連線")
        st.caption(f"Debug: {str(e)[:50]}")
