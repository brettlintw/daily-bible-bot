import streamlit as st
import google.generativeai as genai
from datetime import datetime
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 1. 頁面自適應與 iPhone 螢幕鎖定 ---
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
    /* 修正 iOS 點擊輸入框時的畫面跳動 */
    input, textarea { font-size: 16px !important; }
    #MainMenu, footer, header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 安全密鑰讀取 (防崩潰機制) ---
def get_config(key, backup):
    try:
        return st.secrets[key]
    except:
        return backup

GEMINI_API_KEY = get_config("GEMINI_API_KEY", "AIzaSyC4rqWk4ybph9d5E26QTaGgMlLfU8lg64U")
LINE_ACCESS_TOKEN = get_config("LINE_ACCESS_TOKEN", "vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU=")
LINE_USER_ID = get_config("LINE_USER_ID", "Uf166c741223bc8ee5d82fd1fd9f4df86")

# 系統初始化
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. UI 任務控制中心 ---
st.title("🛡️ 聖經任務控制台")

c1, c2 = st.columns(2)
with c1:
    st.write(f"📅 **{datetime.now().strftime('%Y/%m/%d')}**")
with c2:
    st.write("🛰️ **加密通訊已就緒**")

st.markdown("---")

# ✍️ 自定義任務
st.subheader("✍️ 自定義推送")
custom_msg = st.text_area("訊息內容：", placeholder="在此輸入要發送的文字...", height=120)

if st.button("📤 執行自定義推送任務"):
    if custom_msg.strip():
        try:
            line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【手動自選】\n\n{custom_msg}"))
            st.success("任務送達")
            st.balloons()
        except:
            st.error("通訊異常")
    else:
        st.warning("內容不可為空")

st.markdown("---")

# 🤖 AI 智慧靈糧 (針對 404 報錯進行終極模型校準)
st.subheader("🤖 AI 智慧任務")
if st.button("✨ 啟動 AI 靈糧生成"):
    try:
        with st.spinner("AI 引擎熱機中..."):
            # 修正：加上 models/ 前綴並指定最新穩定版本
            model = genai.GenerativeModel('models/gemini-1.5-flash')
            
            # 使用明確的 Prompt
            response = model.generate_content("請提供一段聖經經文與50字內的鼓勵啟示，語氣專業且溫暖。")
            
            if response and response.text:
                line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【AI 智慧推送】\n\n{response.text}"))
                st.success("AI 任務已成功送達")
                st.balloons()
            else:
                st.error("生成內容缺失")
    except Exception as e:
        # 捕捉精確錯誤
        st.error("AI 引擎連線失敗")
        st.caption(f"診斷日誌: {str(e)[:60]}...")

st.caption("系統版本: CL3-Elite-v5.8 (Stable Final)")
