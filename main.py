import streamlit as st
import google.generativeai as genai
from datetime import datetime
import random
import time
import os

# --- 1. 頁面配置 (極致校準一頁式) ---
st.set_page_config(page_title="聖經控制台 V11.9", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .main .block-container { max-width: 80% !important; padding: 0.3rem 1rem !important; overflow: hidden !important; }
    @media (max-width: 1023px) { .main .block-container { max-width: 100% !important; padding: 0.3rem !important; } }
    h1 { font-size: 1.2rem !important; margin: 0 !important; line-height: 1.1 !important; color: #E0E0E0; }
    hr { margin: 0.25rem 0 !important; }
    .stTextArea>div>div>textarea { height: 55px !important; border-radius: 8px; font-size: 14px !important; }
    .stTextInput>div>div>input { height: 2.2rem !important; border-radius: 8px; font-size: 14px !important; }
    .stSelectbox>div>div { height: 2.2rem !important; font-size: 13px !important; display: flex; align-items: center; }
    .stButton>button { border-radius: 8px; height: 2.4rem; font-weight: bold; font-size: 14px !important; }
    .log-box { font-size: 0.65rem; background: #121212; color: #00FF41; padding: 6px; border-radius: 8px; font-family: monospace; border: 1px solid #333; height: 60px; overflow-y: auto; }
    [data-testid="stHeader"], footer, #MainMenu { visibility: hidden; height: 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心組件與雲端同步邏輯 ---
DB_FILE = "schedule_db.txt" # 雲端持久化文件

def save_to_cloud(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        f.write(data)

def load_from_cloud():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "06:30, 08:00, 12:00, 21:00" # 初始預設值

def get_cfg(key, fallback):
    try: return st.secrets.get(key, fallback) or fallback
    except: return fallback

GEMINI_API_KEY = get_cfg("GEMINI_API_KEY", "")
LINE_TOKEN = get_cfg("LINE_ACCESS_TOKEN", "")

if 'sys_log' not in st.session_state: st.session_state.sys_log = []

def add_log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.sys_log.insert(0, f"[{ts}] {msg}")
    if len(st.session_state.sys_log) > 3: st.session_state.sys_log.pop()

from linebot import LineBotApi
from linebot.models import TextSendMessage
line_api = LineBotApi(LINE_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. UI 佈局 ---
st.title("🛡️ 聖經任務控制台+LINE推送 V11.9")
st.caption(f"📅 {datetime.now().strftime('%m/%d')} | 🛰️ 跨裝置同步模式")

# ⏰ 排程管理 (實現雲端讀寫)
with st.expander("⏰ 推送排程同步設定", expanded=False):
    current_val = load_from_cloud() # 每次都從雲端文件讀取
    schedule_input = st.text_input("24h 時段 (用逗號隔開)：", value=current_val, label_visibility="collapsed")
    
    if st.button("💾 全裝置同步保存"):
        save_to_cloud(schedule_input)
        add_log(f"雲端已同步: {schedule_input[:15]}...")
        st.toast("✅ 已寫入雲端，各裝置將同步生效")

# ✍️ 手動廣播
with st.form("manual_form", clear_on_submit=True):
    st.subheader("✍️ 手動廣播")
    custom_text = st.text_area("內容：", placeholder="在此輸入...", label_visibility="collapsed")
    if st.form_submit_button("📢 執行全員廣播"):
        if custom_text.strip():
            try:
                line_api.broadcast(TextSendMessage(text=f"【手動推送】\n\n{custom_text}"))
                add_log("廣播成功")
                st.toast("✅ 已送達")
            except: st.error("連線異常")

st.markdown("---")

# 🤖 AI 智慧廣播
st.subheader("🤖 AI 智慧廣播")
c1, c2, c3 = st.columns([1, 1, 1])
with c1: mood_input = st.text_input("心情：", placeholder="心情...", label_visibility="collapsed")
with c2: persona = st.selectbox("風格：", ["暖心", "專業", "KITT"], index=0, label_visibility="collapsed")
with c3: content_type = st.selectbox("內容：", ["聖經經文", "推薦詩歌"], index=0, label_visibility="collapsed")

if st.button("✨ 啟動 AI 智慧推送"):
    try:
        models = [m.name for m in genai.list_models()]
        target_model = next((n for n in models if 'flash' in n), models[0])
        model = genai.GenerativeModel(target_model)
        persona_map = {"暖心": "溫柔牧者。", "專業": "分析師。", "KITT": "KITT，稱呼Brett。"}
        
        prompt = f"Time:{time.time()}。{persona_map[persona]} 針對『{mood_input if mood_input else '信仰'}』選經文並啟示。80字內。"
        if content_type == "推薦詩歌":
            prompt = f"Time:{time.time()} 針對『{mood_input if mood_input else '疲累'}』推薦詩歌含歌詞。80字內。"

        res = model.generate_content(prompt)
        if res and res.text:
            header = "【AI經文推送】" if content_type == "聖經經文" else "【AI詩歌推薦】"
            line_api.broadcast(TextSendMessage(text=f"{header}\n\n{res.text}"))
            add_log(f"AI {content_type[:2]}成功")
            st.toast("✨ 廣播完成")
    except Exception as e:
        if "429" in str(e):
            st.warning("配額上限")
            add_log("429 封鎖")
        else: st.error("對接失敗")

# 📡 系統日誌
st.markdown("---")
if st.session_state.sys_log:
    st.markdown(f"<pre class='log-box'>{chr(10).join(st.session_state.sys_log)}</pre>", unsafe_allow_html=True)
