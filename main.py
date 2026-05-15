import streamlit as st
import google.generativeai as genai
from datetime import datetime
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 1. 行動端優化配置 (解決版面跑位與跳頁) ---
st.set_page_config(
    page_title="聖經 AI 控制台",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 注入 CSS：徹底鎖定手機寬度，防止橫向滑動與自動縮放
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
    /* 修正 iOS 點擊輸入框時的畫面自動縮放 */
    input, textarea { font-size: 16px !important; }
    #MainMenu, footer, header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 安全密鑰讀取機制 ---
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

# --- 3. UI 任務控制台 ---
st.title("🛡️ 聖經任務控制台")

c1, c2 = st.columns(2)
with c1:
    st.write(f"📅 **{datetime.now().strftime('%Y/%m/%d')}**")
with c2:
    st.write("🛰️ **5G 安全加密連線**")

st.markdown("---")

# ✍️ 自定義推送
st.subheader("✍️ 自定義推送")
custom_msg = st.text_area("訊息內容：", placeholder="貼上經文或心情...", height=120)

if st.button("📤 執行自定義推送任務"):
    if custom_msg.strip():
        try:
            line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【手動自選】\n\n{custom_msg}"))
            st.success("任務已送達")
            st.balloons()
        except:
            st.error("連線異常")
    else:
        st.warning("內容不可為空")

st.markdown("---")

# 🤖 AI 智慧靈糧 (徹底修正 404 調用失敗問題)
st.subheader("🤖 AI 智慧任務")
if st.button("✨ 啟動 AI 靈糧生成"):
    try:
        with st.spinner("AI 引擎熱機中..."):
            # 核心修正：直接使用 'gemini-1.5-flash' 名稱，不帶 models/ 前綴
            # 這是目前穩定版 SDK 對於 Streamlit 雲端環境最穩定的調用方式
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            response = model.generate_content("請提供一段聖經經文與50字內的鼓勵啟示，語氣專業且溫暖。")
            
            if response and response.text:
                line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【AI 任務推送】\n\n{response.text}"))
                st.success("AI 任務送達成功")
                st.balloons()
            else:
                st.error("生成內容空白")
    except Exception as e:
        st.error("AI 引擎調用失敗")
        st.caption(f"技術日誌: {str(e)[:100]}")

st.caption("系統版本: CL3-Elite-v6.1 (Stable Final)")
