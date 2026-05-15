import streamlit as st
import google.generativeai as genai
from datetime import datetime
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 1. 行動端優化配置 ---
st.set_page_config(
    page_title="聖經 AI 控制台",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 注入 CSS：鎖定手機寬度，防止橫向捲動與跳頁
st.markdown("""
    <style>
    /* 移除邊距並鎖定寬度 */
    .block-container {
        padding: 1rem !important;
        max-width: 100vw !important;
        overflow-x: hidden;
    }
    /* 按鈕手機化 */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.5rem;
        font-weight: 700;
        margin-top: 10px;
    }
    /* 防止鍵盤彈出時縮放 */
    input, textarea { font-size: 16px !important; }
    /* 隱藏預設元件 */
    #MainMenu, footer, header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 安全密鑰管理 ---
def get_secret(key, backup):
    try:
        return st.secrets[key]
    except:
        return backup

# 讀取密鑰
GEMINI_API_KEY = get_secret("GEMINI_API_KEY", "AIzaSyC4rqWk4ybph9d5E26QTaGgMlLfU8lg64U")
LINE_ACCESS_TOKEN = get_secret("LINE_ACCESS_TOKEN", "vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU=")
LINE_USER_ID = get_secret("LINE_USER_ID", "Uf166c741223bc8ee5d82fd1fd9f4df86")

# 初始化
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. 控制台介面 ---
st.title("🛡️ 聖經任務控制台")

# 狀態列
c1, c2 = st.columns(2)
with c1:
    st.write(f"📅 **{datetime.now().strftime('%Y/%m/%d')}**")
with c2:
    st.write("🛰️ **5G 安全連線**")

st.markdown("---")

# ✍️ 自定義推送
st.subheader("✍️ 自定義推送")
custom_msg = st.text_area("內容：", placeholder="貼上經文或心情...", height=100)

if st.button("📤 執行自定義任務"):
    if custom_msg.strip():
        try:
            line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【自選經文】\n\n{custom_msg}"))
            st.success("傳送成功")
            st.balloons()
        except:
            st.error("連線超時")
    else:
        st.warning("請輸入內容")

st.markdown("---")

# 🤖 AI 智慧生成 (修復 404 問題)
st.subheader("🤖 AI 智慧推送")
if st.button("✨ 啟動 AI 靈糧生成"):
    try:
        with st.spinner("正在呼叫 AI 核心..."):
            # 修正：使用全名模型路徑，確保 API 能正確抓取
            model = genai.GenerativeModel(model_name='gemini-1.5-flash')
            prompt = "請提供一段充滿力量的聖經經文與50字內的啟示，語氣溫和專業。"
            response = model.generate_content(prompt)
            
            if response.text:
                line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【AI 推送】\n\n{response.text}"))
                st.success("AI 任務已送達")
                st.balloons()
            else:
                st.error("生成內容空白")
    except Exception as e:
        st.error("AI 模組調用失敗")
        # 顯示更精簡的日誌資訊
        st.caption(f"Log: {str(e)[:100]}...")

st.caption("系統版本: CL3-Elite-v5.0 (Stable Final)")
