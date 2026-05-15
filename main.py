import streamlit as st
import google.generativeai as genai
from datetime import datetime
import random
import time
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 1. 頁面配置 ---
st.set_page_config(page_title="聖經控制台 V10.4", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

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
    try: return st.secrets.get(key, fallback) or fallback
    except: return fallback

GEMINI_API_KEY = get_cfg("GEMINI_API_KEY", "")
LINE_TOKEN = get_cfg("LINE_ACCESS_TOKEN", "")

if 'sys_log' not in st.session_state:
    st.session_state.sys_log = []

def add_log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.sys_log.insert(0, f"[{ts}] {msg}")
    if len(st.session_state.sys_log) > 5: st.session_state.sys_log.pop()

if not GEMINI_API_KEY or not LINE_TOKEN:
    st.error("❌ 核心金鑰未就緒")
    st.stop()

@st.cache_resource
def init_apis():
    line = LineBotApi(LINE_TOKEN)
    genai.configure(api_key=GEMINI_API_KEY)
    return line

line_api = init_apis()

# --- 3. UI 介面佈局 ---
st.title("🛡️ 聖經任務控制台 V10.4")
st.caption(f"📅 {datetime.now().strftime('%m/%d')} | 🛰️ 流量抗壓與自動清除 | v10.4")

# ⏰ 多重排程設定
st.subheader("⏰ 多重排程推送")
schedules = st.multiselect("排程時段：", ["06:30", "07:00", "08:00", "09:00", "12:00", "18:00", "21:00"], default=["06:30", "08:00"], label_visibility="collapsed")
if st.button("💾 更新排程設定"):
    add_log(f"排程更新: {', '.join(schedules)}")
    st.toast("✅ 排程已備存")

st.markdown("---")

# ✍️ 即時廣播 (自動清除)
st.subheader("✍️ 即時廣播傳輸")
with st.form("broadcast_form", clear_on_submit=True):
    custom_text = st.text_area("內容：", placeholder="在此輸入內容...", label_visibility="collapsed", height=100)
    if st.form_submit_button("📢 執行全員廣播"):
        if custom_text.strip():
            try:
                line_api.broadcast(TextSendMessage(text=f"【特別推送】\n\n{custom_text}"))
                add_log("全員廣播成功")
                st.toast("✅ 已送達所有好友")
            except Exception as e:
                add_log(f"廣播異常: {str(e)[:20]}")
                st.error("連線異常")

st.markdown("---")

# 🤖 AI 智慧廣播 (修正 429 流量錯誤)
st.subheader("🤖 AI 智慧廣播")
mood_input = st.text_input("今日心情：", placeholder="例如：挑戰、疲累...")
persona = st.selectbox("風格：", ["溫暖啟發 (暖心)", "冷靜理性 (專業)", "K.I.T.T. 霹靂語調"], index=0)

if st.button("✨ 啟動 AI 廣播推送"):
    try:
        with st.spinner("AI 頻道修復與導引中..."):
            models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            target_model = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in models else models[0]
            
            persona_map = {
                "溫暖啟發 (暖心)": "你是溫柔牧者，充滿靈性。",
                "冷靜理性 (專業)": "你是分析師，簡練專業。",
                "K.I.T.T. 霹靂語調": "你是K.I.T.T.，稱呼Brett，語氣冷靜專業。"
            }
            
            model = genai.GenerativeModel(target_model)
            prompt = f"{persona_map[persona]} 針對『{mood_input if mood_input else '隨機力量'}』主題，選一段經文並給予80字內啟示。隨機指紋:{time.time()}。"
            
            # 實施抗壓機制：若遇到 429 則短暫重試
            res = None
            for i in range(2): # 嘗試 2 次
                try:
                    res = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.9))
                    break
                except Exception as e:
                    if "429" in str(e):
                        time.sleep(2) # 等待 2 秒
                        continue
                    raise e

            if res and hasattr(res, 'text'):
                line_api.broadcast(TextSendMessage(text=f"【AI智慧推送】\n\n{res.text}"))
                add_log(f"AI 廣播完成 ({persona[:2]})")
                st.toast("✨ 推送達成")
    except Exception as e:
        add_log(f"連線異常: {str(e)[:30]}")
        st.error("AI 目前頻繁請求中，請 30 秒後再試。")

st.markdown("---")

# 📡 系統運行日誌
st.subheader("📡 系統運行日誌")
if st.session_state.sys_log:
    st.markdown(f"<pre class='log-box'>{chr(10).join(st.session_state.sys_log)}</pre>", unsafe_allow_html=True)
