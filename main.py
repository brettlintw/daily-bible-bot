import streamlit as st
import google.generativeai as genai
from datetime import datetime
import random
import time

# --- 1. 頁面配置與一頁式 CSS ---
st.set_page_config(page_title="聖經控制台 V10.9", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

# 注入 CSS：精簡間距、字體、高度，確保不產生捲軸
st.markdown("""
    <style>
    /* 核心外框比例控制與捲軸隱藏 */
    .main .block-container {
        max-width: 80% !important;
        padding: 0.5rem !important;
        overflow-y: hidden !important;
    }
    @media (max-width: 1023px) { .main .block-container { max-width: 100% !important; } }
    
    /* 標題與文字緊湊化 */
    h1 { font-size: 1.1rem !important; margin: 0 !important; line-height: 1.2 !important; }
    h3 { font-size: 0.9rem !important; margin-bottom: 0.2rem !important; }
    .stCaption { margin-bottom: 0.4rem !important; }
    hr { margin: 0.4rem 0 !important; }
    
    /* 輸入框與按鈕精簡化 */
    .stTextArea>div>div>textarea { height: 70px !important; border-radius: 10px; }
    .stTextInput>div>div>input { height: 2rem !important; border-radius: 10px; }
    .stButton>button { border-radius: 10px; height: 2.8rem; font-weight: bold; }
    .stSelectbox>div>div { height: 2.2rem !important; }
    
    /* 日誌區塊高度限制 */
    .log-box { 
        font-size: 0.7rem; background: #121212; color: #00FF41; 
        padding: 8px; border-radius: 8px; font-family: monospace; 
        border: 1px solid #333; height: 100px; overflow-y: auto;
    }
    [data-testid="stHeader"], footer, #MainMenu { visibility: hidden; height: 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心組件 (保留原邏輯) ---
def get_cfg(key, fallback):
    try: return st.secrets.get(key, fallback) or fallback
    except: return fallback

GEMINI_API_KEY = get_cfg("GEMINI_API_KEY", "")
LINE_TOKEN = get_cfg("LINE_ACCESS_TOKEN", "")

if 'sys_log' not in st.session_state: st.session_state.sys_log = []

def add_log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.sys_log.insert(0, f"[{ts}] {msg}")
    if len(st.session_state.sys_log) > 4: st.session_state.sys_log.pop()

@st.cache_resource
def init_apis():
    from linebot import LineBotApi
    line = LineBotApi(LINE_TOKEN)
    genai.configure(api_key=GEMINI_API_KEY)
    return line

if not GEMINI_API_KEY or not LINE_TOKEN:
    st.error("❌ 金鑰未設定")
    st.stop()

line_api = init_apis()

# --- 3. UI 一頁式佈局 ---
st.title("🛡️ 聖經任務控制台 V10.9")
st.caption(f"📅 {datetime.now().strftime('%m/%d')} | v10.9-Compact")

# ✍️ 即時廣播
from linebot.models import TextSendMessage
with st.form("broadcast_form", clear_on_submit=True):
    custom_text = st.text_area("廣播內容：", placeholder="在此輸入...", label_visibility="collapsed")
    if st.form_submit_button("📢 執行全員廣播"):
        if custom_text.strip():
            try:
                line_api.broadcast(TextSendMessage(text=f"【特別推送】\n\n{custom_text}"))
                add_log("廣播成功")
                st.toast("✅ 已送達")
            except: st.error("異常")

st.markdown("---")

# 🤖 AI 智慧廣播
st.subheader("🤖 AI 智慧廣播")
c1, c2 = st.columns([1, 1])
with c1: mood_input = st.text_input("心情：", placeholder="挑戰...", label_visibility="collapsed")
with c2: persona = st.selectbox("風格：", ["暖心", "專業", "KITT"], index=0, label_visibility="collapsed")

if st.button("✨ 啟動 AI 廣播"):
    status = st.empty()
    try:
        all_models = [m.name for m in genai.list_models()]
        flash_models = [n for n in all_models if 'flash' in n]
        target_model = flash_models[0] if flash_models else all_models[0]
        
        persona_map = {"暖心": "溫柔牧者。", "專業": "精確分析師。", "KITT": "K.I.T.T.，稱呼Brett。"}
        model = genai.GenerativeModel(target_model)
        prompt = f"{persona_map[persona]} 針對『{mood_input if mood_input else '隨機信仰力量'}』選經文並給予80字內啟示。隨機ID:{random.random()}"

        res = None
        for attempt in range(2):
            try:
                res = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.9))
                break 
            except Exception as e:
                if "429" in str(e) and attempt == 0:
                    time.sleep(3)
                    continue
                raise e

        if res and hasattr(res, 'text'):
            line_api.broadcast(TextSendMessage(text=f"【AI智慧推送】\n\n{res.text}"))
            add_log(f"AI 推送成功")
            st.toast("✨ 廣播完成")
        else: st.error("生成異常")
    except Exception as e:
        add_log(f"連線異常")
        st.error(f"連線失敗: {str(e)[:20]}")

st.markdown("---")
# 📡 系統日誌
if st.session_state.sys_log:
    log_text = chr(10).join(st.session_state.sys_log)
    st.markdown(f"<pre class='log-box'>{log_text}</pre>", unsafe_allow_html=True)
