import streamlit as st
import google.generativeai as genai
from datetime import datetime
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 1. 手機全螢幕自適應配置 ---
st.set_page_config(
    page_title="聖經 AI 控制台",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 注入 CSS：鎖定手機寬度、防止橫向溢出、優化按鈕點擊感
st.markdown("""
    <style>
    .block-container {
        padding: 1rem !important;
        max-width: 100vw !important;
        overflow-x: hidden;
    }
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.8rem;
        font-weight: 700;
        margin-top: 10px;
        background-color: #007AFF;
        color: white;
    }
    /* 修正 iOS 鍵盤彈出導致的縮放位移 */
    input, textarea { font-size: 16px !important; }
    /* 隱藏不必要的網頁元素 */
    #MainMenu, footer, header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 安全密鑰管理邏輯 ---
def get_config(key, backup):
    try:
        return st.secrets[key]
    except:
        return backup

GEMINI_API_KEY = get_config("GEMINI_API_KEY", "AIzaSyC4rqWk4ybph9d5E26QTaGgMlLfU8lg64U")
LINE_ACCESS_TOKEN = get_config("LINE_ACCESS_TOKEN", "vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU=")
LINE_USER_ID = get_config("LINE_USER_ID", "Uf166c741223bc8ee5d82fd1fd9f4df86")

# 初始化通訊組件
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. UI 控制中心 ---
st.title("🛡️ 聖經任務控制台")

# 狀態資訊
c1, c2 = st.columns(2)
with c1:
    st.write(f"📅 **{datetime.now().strftime('%Y/%m/%d')}**")
with c2:
    st.write("🛰️ **5G 安全加密連線**")

st.markdown("---")

# ✍️ 自定義推送
st.subheader("✍️ 自定義推送")
custom_msg = st.text_area("在此輸入內容：", placeholder="貼上經文或心中感動...", height=120)

if st.button("📤 執行自定義推送任務"):
    if custom_msg.strip():
        try:
            line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【手動自選】\n\n{custom_msg}"))
            st.success("傳送成功")
            st.balloons()
        except Exception as e:
            st.error("連線異常，請檢查網路")
    else:
        st.warning("請輸入內容")

st.markdown("---")

# 🤖 AI 智慧靈糧 (徹底修正 404 調用失敗問題)
st.subheader("🤖 AI 智慧任務")
if st.button("✨ 啟動 AI 靈糧生成"):
    try:
        with st.spinner("AI 引擎熱機中..."):
            # 修正核心：移除 models/ 前綴，直接使用簡潔的模型名稱
            # 這能避開特定版本 SDK 在託管環境下的路徑識別錯誤
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = "請提供一段充滿力量的聖經經文與50字內的啟示，語氣溫暖，適合今日。"
            response = model.generate_content(prompt)
            
            if response and response.text:
                line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【AI 推送任務】\n\n{response.text}"))
                st.success("AI 任務已送達")
                st.balloons()
            else:
                st.error("生成內容空白，請再試一次")
    except Exception as e:
        st.error("AI 引擎調用失敗")
        st.caption(f"診斷日誌: {str(e)[:80]}...")

st.caption("系統版本: CL3-Elite-v5.6 (Stable Final Build)")
