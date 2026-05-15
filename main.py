import streamlit as st
import google.generativeai as genai
from datetime import datetime
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 1. 介面配置與 iPhone 鎖定 ---
st.set_page_config(
    page_title="聖經 AI 控制台",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .block-container { padding: 1.5rem 1rem !important; max-width: 100vw !important; overflow-x: hidden; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5rem; font-weight: 700; background-color: #007AFF; color: white; }
    input, textarea { font-size: 16px !important; }
    #MainMenu, footer, header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 安全密鑰管理 ---
def get_config(key, backup):
    try: return st.secrets[key]
    except: return backup

GEMINI_API_KEY = get_config("GEMINI_API_KEY", "AIzaSyC4rqWk4ybph9d5E26QTaGgMlLfU8lg64U")
LINE_ACCESS_TOKEN = get_config("LINE_ACCESS_TOKEN", "vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU=")
LINE_USER_ID = get_config("LINE_USER_ID", "Uf166c741223bc8ee5d82fd1fd9f4df86")

# 初始化
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. UI 控制中心 ---
st.title("🛡️ 聖經任務控制台")
st.write(f"📅 **{datetime.now().strftime('%Y/%m/%d')}** | 🛰️ **加密連線中**")
st.markdown("---")

# ✍️ 自定義推送
st.subheader("✍️ 自定義推送")
custom_msg = st.text_area("內容：", placeholder="貼上經文...", height=100)
if st.button("📤 執行自定義任務"):
    if custom_msg.strip():
        try:
            line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【自選經文】\n\n{custom_msg}"))
            st.success("傳送成功")
            st.balloons()
        except: st.error("連線超時")

st.markdown("---")

# 🤖 AI 智慧任務 (自動掃描可用模型，破解 404 死迴圈)
st.subheader("🤖 AI 智慧任務")
if st.button("✨ 啟動 AI 靈糧生成"):
    try:
        with st.spinner("正在掃描可用 AI 引擎..."):
            # 自動找尋帳號下支援生成內容的模型
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            # 優先找 flash，找不到就找 pro，再找不到就選第一個
            target_model = next((m for m in available_models if "flash" in m), 
                                next((m for m in available_models if "pro" in m), 
                                     available_models[0] if available_models else None))
            
            if not target_model:
                st.error("找不到可用的 AI 模型")
            else:
                st.caption(f"已自動掛載引擎: {target_model}")
                model = genai.GenerativeModel(target_model)
                response = model.generate_content("請提供一段充滿力量的聖經經文與50字內的啟示，語氣溫暖。")
                
                if response.text:
                    line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【AI 推送】\n\n{response.text}"))
                    st.success("AI 任務已送達")
                    st.balloons()
    except Exception as e:
        st.error("AI 引擎自動掛載失敗")
        st.caption(f"技術日誌: {str(e)}")

st.caption("系統版本: CL3-Elite-v7.0 (Auto-Scan Stable)")
