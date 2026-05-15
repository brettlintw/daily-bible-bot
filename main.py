import streamlit as st
import google.generativeai as genai
from datetime import datetime
import random
import time
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 1. 頁面配置 ---
st.set_page_config(
    page_title="聖經控制台 V10.2",
    page_icon="🛡️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 注入 CSS
st.markdown("""
    <style>
    .block-container { padding: 0.8rem 0.8rem !important; max-width: 100vw !important; overflow-x: hidden; }
    h1 { font-size: 1.3rem !important; margin: 0 !important; color: #E0E0E0; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.2rem; font-weight: bold; }
    [data-testid="stHeader"], footer, #MainMenu { visibility: hidden; height: 0; }
    .log-box { font-size: 0.75rem; background: #121212; color: #00FF41; padding: 12px; border-radius: 8px; font-family: monospace; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 安全密鑰與狀態檢查 ---
def get_cfg(key, fallback):
    try:
        val = st.secrets.get(key, fallback)
        return val if val else fallback
    except: return fallback

GEMINI_API_KEY = get_cfg("GEMINI_API_KEY", "")
LINE_TOKEN = get_cfg("LINE_ACCESS_TOKEN", "")
LINE_ID = get_cfg("LINE_USER_ID", "")

if 'sys_log' not in st.session_state:
    st.session_state.sys_log = []

def add_log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.sys_log.insert(0, f"[{ts}] {msg}")
    if len(st.session_state.sys_log) > 5: st.session_state.sys_log.pop()

if not GEMINI_API_KEY or not LINE_TOKEN:
    st.error("❌ 核心通訊組件未就緒")
    st.stop()

@st.cache_resource
def init_apis():
    line = LineBotApi(LINE_TOKEN)
    genai.configure(api_key=GEMINI_API_KEY)
    return line

line_api = init_apis()

# --- 3. UI 介面佈局 ---
st.title("🛡️ 聖經任務控制台 V10.2")
st.caption(f"📅 {datetime.now().strftime('%m/%d')} | 🛰️ 任務傳輸自動清除模式 | v10.2-Fix")

# ✍️ 即時傳輸 (導入自動清除邏輯)
st.subheader("✍️ 即時傳輸")

# 使用 st.form 來實現點擊後自動重置 (Clear on submit)
with st.form("manual_push_form", clear_on_submit=True):
    custom_text = st.text_area("內容：", placeholder="在此輸入內容...", label_visibility="collapsed", height=100)
    submitted = st.form_submit_button("📤 執行手動推送")
    
    if submitted:
        if custom_text.strip():
            try:
                line_api.push_message(LINE_ID, TextSendMessage(text=f"【手動推送】\n\n{custom_text}"))
                add_log("手動傳輸成功並已清空輸入框")
                st.toast("✅ 訊息已送達，輸入框已重置")
            except Exception as e:
                add_log(f"傳輸異常: {str(e)[:20]}")
                st.error("傳輸失敗，請檢查連線。")
        else:
            st.warning("請先輸入內容。")

st.markdown("---")

# 🤖 AI 智慧處方箋
st.subheader("🤖 AI 智慧處方箋")
mood_input = st.text_input("今日心情 (選填)：", placeholder="例如：挑戰、疲累...")
persona = st.selectbox("AI 回覆風格：", ["溫暖啟發 (暖心)", "冷靜理性 (專業)", "K.I.T.T. 霹靂語調 (影集風格)"], index=0)

if st.button("✨ 啟動 AI 智慧推送"):
    try:
        with st.spinner("AI 分析中..."):
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target_model = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in models else models[0]
            
            seed = f"{time.time()}"
            persona_map = {
                "溫暖啟發 (暖心)": "你是溫柔牧者，語氣鼓勵。",
                "冷靜理性 (專業)": "你是專業分析師，語氣簡練。",
                "K.I.T.T. 霹靂語調 (影集風格)": "你是 K.I.T.T.，稱呼 Brett，語氣專業冷靜帶微幽默。"
            }
            
            prompt = f"指紋:{seed}。{persona_map[persona]} 針對主題『{mood_input if mood_input else '隨機信仰力量'}』，挑選合適聖經經文並給予80字內啟示。直接輸出內容。"
            
            model = genai.GenerativeModel(target_model)
            res = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.92))
            
            if res and hasattr(res, 'text'):
                line_api.push_message(LINE_ID, TextSendMessage(text=f"【AI智慧推送】\n\n{res.text}"))
                add_log(f"AI 推送完成 ({persona[:2]})")
                st.toast("✨ 任務達成")
                st.success("AI 智慧推送成功")
    except Exception as e:
        add_log(f"AI故障: {str(e)[:20]}")
        st.error("AI 連線異常")

st.markdown("---")

# 📡 系統運行日誌
st.subheader("📡 系統運行日誌")
if st.session_state.sys_log:
    log_text = "\n".join(st.session_state.sys_log)
    st.markdown(f"<pre class='log-box'>{log_text}</pre>", unsafe_allow_html=True)
else:
    st.caption("目前無通訊紀錄")
