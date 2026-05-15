import streamlit as st
import google.generativeai as genai
from datetime import datetime
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 1. 頁面配置與 iPhone 螢幕鎖定 (解決版面跑掉問題) ---
st.set_page_config(
    page_title="聖經 AI 控制台",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 注入 CSS：鎖定手機寬度，防止橫向滑動與 iOS 自動縮放跳位
st.markdown("""
    <style>
    .block-container {
        padding: 1.5rem 1rem !important;
        max-width: 100vw !important;
        overflow-x: hidden;
    }
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.8rem;
        font-weight: 700;
        background-color: #007AFF;
        color: white;
        margin-top: 10px;
    }
    /* 修正 iOS 點擊輸入框時的畫面縮放 */
    input, textarea { font-size: 16px !important; }
    #MainMenu, footer, header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 安全密鑰管理 ---
def get_config(key, backup):
    try:
        return st.secrets[key]
    except:
        return backup

GEMINI_API_KEY = get_config("GEMINI_API_KEY", "AIzaSyC4rqWk4ybph9d5E26QTaGgMlLfU8lg64U")
LINE_ACCESS_TOKEN = get_config("LINE_ACCESS_TOKEN", "vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU=")
LINE_USER_ID = get_config("LINE_USER_ID", "Uf166c741223bc8ee5d82fd1fd9f4df86")

# 初始化連線
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. UI 控制中心 ---
st.title("🛡️ 聖經任務控制台")

c1, c2 = st.columns(2)
with c1:
    st.write(f"📅 **{datetime.now().strftime('%Y/%m/%d')}**")
with c2:
    st.write("🛰️ **加密連線中**")

st.markdown("---")

# ✍️ 自定義任務
st.subheader("✍️ 自定義推送")
custom_msg = st.text_area("內容：", placeholder="輸入要發送的文字...", height=120)

if st.button("📤 執行自定義推送任務"):
    if custom_msg.strip():
        try:
            line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【手動自選】\n\n{custom_msg}"))
            st.success("任務已送達")
            st.balloons()
        except:
            st.error("連線異常")
    else:
        st.warning("請輸入內容")

st.markdown("---")

# 🤖 AI 智慧靈糧 (修正模型找不到 404 問題)
st.subheader("🤖 AI 智慧任務")
if st.button("✨ 啟動 AI 靈糧生成"):
    try:
        with st.spinner("AI 引擎啟動中..."):
            # 修正核心：移除 models/ 前綴，直接使用模型名稱字串
            # 這是目前 Streamlit 雲端環境最穩定的調用法
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            response = model.generate_content("請提供一段聖經經文與一段鼓勵啟示，限制在100字內。")
            
            if response and response.text:
                line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【AI 推送】\n\n{response.text}"))
                st.success("AI 任務送達")
                st.balloons()
            else:
                st.error("內容生成空白")
    except Exception as e:
        st.error("AI 引擎調用失敗")
        st.caption(f"Debug: {str(e)[:50]}")

st.caption("系統版本: CL3-Elite-v5.9 (Stable Final)")
