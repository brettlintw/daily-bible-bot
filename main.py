import streamlit as st
import google.generativeai as genai
from datetime import datetime
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 1. 手機版全螢幕自適應配置 ---
st.set_page_config(
    page_title="K.I.T.T. 控制台",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 注入 CSS 解決版面溢出與跳頁問題
st.markdown("""
    <style>
    /* 移除頂部空白，鎖定手機寬度 */
    .block-container {
        padding: 1rem !important;
        max-width: 100vw !important;
        overflow-x: hidden;
    }
    /* 讓按鈕與輸入框高度適合手指點擊 */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.5rem;
        font-weight: 700;
        margin-top: 5px;
    }
    /* 優化文字區域，防止鍵盤彈出時版面位移 */
    .stTextArea>div>div>textarea {
        border-radius: 12px;
        font-size: 16px !important; /* 防止 iOS 自動縮放 */
    }
    /* 隱藏 Streamlit 預設選單與頁尾，讓它更像原生 App */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. 安全密鑰讀取機制 ---
def get_config(key, fallback):
    try:
        return st.secrets[key]
    except:
        return fallback

GEMINI_API_KEY = get_config("GEMINI_API_KEY", "AIzaSyC4rqWk4ybph9d5E26QTaGgMlLfU8lg64U")
LINE_ACCESS_TOKEN = get_config("LINE_ACCESS_TOKEN", "vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU=")
LINE_USER_ID = get_config("LINE_USER_ID", "Uf166c741223bc8ee5d82fd1fd9f4df86")

# 初始化通訊組件
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. UI 任務控制台 ---
st.title("🛡️ 聖經任務控制台")

# 狀態列：使用橫向排列
c1, c2 = st.columns(2)
with c1:
    st.caption("今日日期")
    st.write(f"**{datetime.now().strftime('%Y/%m/%d')}**")
with c2:
    st.caption("傳輸協定")
    st.write("**5G / Encrypted**")

st.markdown("---")

# ✍️ 自定義經文任務
st.subheader("✍️ 自定義推送")
custom_verse = st.text_area("內容：", placeholder="在此輸入或貼上聖經經文...", height=100)

if st.button("📤 執行自定義推送"):
    if custom_verse.strip():
        try:
            line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【手動自選經文】\n\n{custom_verse}"))
            st.success("推送成功")
            st.balloons()
        except Exception as e:
            st.error("傳輸中斷")
    else:
        st.warning("內容不可為空")

st.markdown("---")

# 🤖 AI 智慧靈糧 (徹底修正 404 模型路徑問題)
st.subheader("🤖 AI 智慧推送")
if st.button("✨ 啟動 AI 生成"):
    try:
        with st.spinner("正在呼叫 Gemini 核心..."):
            # 修正：移除 models/ 前綴，使用最穩定的字串名稱
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = "請挑選一段充滿力量的聖經經文與啟示，語氣溫暖，限制在80字內。"
            response = model.generate_content(prompt)
            
            if response and response.text:
                line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【AI 推送任務】\n\n{response.text}"))
                st.success("AI 任務已送達")
            else:
                st.error("內容生成失敗")
    except Exception as e:
        # 如果還是 404，程式會自動捕獲並提示
        st.error("AI 模組調用失敗，請確認 API 權限。")
        st.caption(f"系統日誌: {str(e)}")

st.caption("系統版本: CL3-Elite-v4.2 (Mobile Final)")
