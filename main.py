import streamlit as st
import google.generativeai as genai
from datetime import datetime
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 1. 頁面極簡配置 (防止手機溢出) ---
st.set_page_config(page_title="聖經控制台", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

# 注入 CSS：強制縮減所有元件間距，鎖定手機寬度防止位移
st.markdown("""
    <style>
    .block-container { padding: 0.5rem 0.7rem !important; max-width: 100vw !important; overflow-x: hidden; }
    h1 { font-size: 1.3rem !important; margin: 0 !important; padding: 0 !important; }
    h3 { font-size: 0.95rem !important; margin: 0.4rem 0 !important; }
    .stButton>button { width: 100%; border-radius: 8px; height: 2.5rem; font-weight: 600; font-size: 0.9rem; }
    .stTextArea>div>div>textarea { border-radius: 8px; font-size: 15px !important; height: 75px !important; }
    .stSelectbox div[data-baseweb="select"] { min-height: 2rem; }
    [data-testid="stHeader"], footer, #MainMenu { visibility: hidden; height: 0; }
    hr { margin: 0.4rem 0 !important; }
    div.stText { font-size: 0.7rem !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 安全密鑰讀取 (使用 st.secrets) ---
def get_cfg(key, fallback):
    try: return st.secrets[key]
    except: return fallback

GEMINI_API_KEY = get_cfg("GEMINI_API_KEY", "AIzaSyC4rqWk4ybph9d5E26QTaGgMlLfU8lg64U")
LINE_TOKEN = get_cfg("LINE_ACCESS_TOKEN", "vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU=")
LINE_ID = get_cfg("LINE_USER_ID", "Uf166c741223bc8ee5d82fd1fd9f4df86")

# 初始化通訊模組
line_api = LineBotApi(LINE_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. UI 介面佈局 (一頁式設計) ---
st.title("🛡️ 聖經任務控制台")
st.caption(f"📅 {datetime.now().strftime('%m/%d')} | 🛰️ 安全連線 | v7.7")

# ✍️ 即時傳輸任務
st.subheader("✍️ 即時傳輸")
custom_text = st.text_area("內容：", placeholder="在此輸入...", label_visibility="collapsed")
if st.button("📤 執行手動推送"):
    if custom_text.strip():
        try:
            line_api.push_message(LINE_ID, TextSendMessage(text=f"【手動推送】\n\n{custom_text}"))
            st.toast("✅ 已送達")
        except: st.error("傳輸失敗")

st.markdown("---")

# 🤖 AI 排程與生成 (參考成功版本修正模型路徑)
st.subheader("⏰ AI 排程與推送")
t_list = ["06:30", "07:00", "08:00", "09:00"]
selected_t = st.selectbox("時間：", t_list, index=2, label_visibility="collapsed")

c1, c2 = st.columns(2)
with c1:
    if st.button("💾 確認設定"): st.toast(f"已排程 {selected_t}")
with c2:
    if st.button("✨ AI 測試"):
        try:
            with st.spinner("系統生成中..."):
                # 修正：針對 404 報錯，回歸最穩定且被廣泛支援的模型 ID
                model = genai.GenerativeModel('gemini-1.5-flash-latest')
                res = model.generate_content("請幫我從聖經中挑選一段適合今日的經文並給予一段溫暖的啟示，總字數限制在80字內。")
                
                if res and res.text:
                    line_api.push_message(LINE_ID, TextSendMessage(text=f"【AI測試】\n\n{res.text}"))
                    st.toast("✨ 推送成功")
                    st.balloons()
                else: st.error("內容生成異常")
        except Exception as e:
            st.error("AI 系統暫時無法連線")
            st.caption(f"Error Code: {str(e)[:50]}")
