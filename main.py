import streamlit as st
import google.generativeai as genai
from datetime import datetime
import random
import time

# --- 1. 頁面配置與一頁式 CSS ---
st.set_page_config(page_title="聖經控制台 V11.0", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .main .block-container { max-width: 80% !important; padding: 0.5rem !important; overflow: hidden !important; }
    @media (max-width: 1023px) { .main .block-container { max-width: 100% !important; } }
    h1 { font-size: 1.1rem !important; margin: 0 !important; }
    .stTextArea>div>div>textarea { height: 70px !important; border-radius: 10px; }
    .stButton>button { border-radius: 10px; height: 2.8rem; font-weight: bold; }
    [data-testid="stHeader"], footer, #MainMenu { visibility: hidden; height: 0; }
    .log-box { font-size: 0.7rem; background: #121212; color: #00FF41; padding: 8px; border-radius: 8px; font-family: monospace; height: 90px; overflow-y: auto; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心組件 ---
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

line_api = init_apis()

# --- 3. UI 一頁式佈局 ---
st.title("🛡️ 聖經任務控制台 V11.0")
st.caption(f"📅 {datetime.now().strftime('%m/%d')} | v11.0-Shield")

# 即時廣播
from linebot.models import TextSendMessage
with st.form("broadcast_form", clear_on_submit=True):
    custom_text = st.text_area("廣播內容：", placeholder="在此輸入...", label_visibility="collapsed")
    if st.form_submit_button("📢 執行全員廣播"):
        if custom_text.strip():
            try:
                line_api.broadcast(TextSendMessage(text=f"【特別推送】\n\n{custom_text}"))
                add_log("廣播成功")
                st.toast("✅ 已送達")
            except: st.error("傳輸異常")

st.markdown("---")

# AI 智慧廣播 (強化 429 錯誤處理)
st.subheader("🤖 AI 智慧廣播")
c1, c2 = st.columns([1, 1])
with c1: mood_input = st.text_input("心情：", placeholder="心情...", label_visibility="collapsed")
with c2: persona = st.selectbox("風格：", ["暖心", "專業", "KITT"], index=0, label_visibility="collapsed")

if st.button("✨ 啟動 AI 廣播"):
    status = st.empty()
    try:
        # 動態掃描可用衛星
        models = [m.name for m in genai.list_models()]
        target_model = [n for n in models if 'flash' in n][0] if any('flash' in n for n in models) else models[0]
        
        persona_map = {"暖心": "溫柔牧者。", "專業": "分析師。", "KITT": "KITT，稱呼Brett。"}
        model = genai.GenerativeModel(target_model)
        prompt = f"{persona_map[persona]} 針對『{mood_input if mood_input else '信仰'}』選經文並給予80字內啟示。ID:{random.random()}"

        res = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.9))

        if res and hasattr(res, 'text'):
            line_api.broadcast(TextSendMessage(text=f"【AI智慧推送】\n\n{res.text}"))
            add_log("AI 推送成功")
            st.toast("✨ 廣播完成")
        else: st.error("衛星內容解析異常")

    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg:
            st.warning("🛑 衛星過熱冷卻中... 請等待約 60 秒後再嘗試。")
            add_log("通訊頻寬封鎖 (429)")
        else:
            st.error(f"連線中斷：{err_msg[:20]}")
            add_log("連線失敗")

st.markdown("---")
if st.session_state.sys_log:
    st.markdown(f"<pre class='log-box'>{chr(10).join(st.session_state.sys_log)}</pre>", unsafe_allow_html=True)
