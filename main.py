import streamlit as st
import google.generativeai as genai
from datetime import datetime
import random
import time

# --- 1. 頁面配置 (精簡一頁式) ---
st.set_page_config(page_title="聖經控制台 V11.4", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .main .block-container { max-width: 80% !important; padding: 0.5rem !important; overflow: hidden !important; }
    @media (max-width: 1023px) { .main .block-container { max-width: 100% !important; } }
    h1 { font-size: 1.1rem !important; margin: 0 !important; }
    .stTextArea>div>div>textarea { height: 60px !important; border-radius: 10px; }
    .stButton>button { border-radius: 10px; height: 2.6rem; font-weight: bold; }
    [data-testid="stHeader"], footer, #MainMenu { visibility: hidden; height: 0; }
    .log-box { font-size: 0.7rem; background: #121212; color: #00FF41; padding: 8px; border-radius: 8px; font-family: monospace; height: 75px; overflow-y: auto; }
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

from linebot import LineBotApi
from linebot.models import TextSendMessage
line_api = LineBotApi(LINE_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. UI 佈局 ---
st.title("🛡️ 聖經任務控制台 V11.4")
st.caption(f"📅 {datetime.now().strftime('%m/%d')} | v11.4-MusicEdition")

# ⏰ 排程管理 (摺疊隱藏)
with st.expander("⏰ 推送排程管理", expanded=False):
    schedules = st.multiselect("設定時段：", ["06:30", "07:00", "08:00", "09:00", "12:00", "21:00"], default=["06:30", "08:00"])
    if st.button("💾 保存設定"):
        add_log(f"排程更新")
        st.toast("✅ 已備份")

# ✍️ 手動全員廣播 (支援手動傳歌曲)
st.subheader("✍️ 手動廣播 (可傳經文或歌曲)")
with st.form("manual_form", clear_on_submit=True):
    custom_text = st.text_area("內容：", placeholder="在此輸入文字或歌曲連結...", label_visibility="collapsed")
    if st.form_submit_button("📢 執行全員廣播"):
        if custom_text.strip():
            try:
                line_api.broadcast(TextSendMessage(text=f"【手動推送】\n\n{custom_text}"))
                add_log("手動廣播完成")
                st.toast("✅ 已送達")
            except: st.error("LINE 通訊異常")

st.markdown("---")

# 🤖 AI 智慧廣播 (新增詩歌選擇開關)
st.subheader("🤖 AI 智慧廣播")
c1, c2, c3 = st.columns([1, 1, 1])
with c1: mood_input = st.text_input("心情：", placeholder="心情...", label_visibility="collapsed")
with c2: persona = st.selectbox("風格：", ["暖心", "專業", "KITT"], index=0, label_visibility="collapsed")
with c3: content_type = st.selectbox("內容：", ["聖經經文", "推薦詩歌"], index=0, label_visibility="collapsed")

if st.button("✨ 啟動 AI 智慧推送"):
    try:
        # 動態鎖定衛星頻道
        models = [m.name for m in genai.list_models()]
        target_model = next((n for n in models if 'flash' in n), models[0])
        model = genai.GenerativeModel(target_model)
        
        persona_map = {"暖心": "溫柔牧者。", "專業": "精確分析師。", "KITT": "K.I.T.T.，稱呼 Brett，語氣幽默冷靜。"}
        
        # 根據開關調整指令
        if content_type == "聖經經文":
            prompt = f"Time:{time.time()}。{persona_map[persona]} 針對『{mood_input if mood_input else '信仰'}』挑選一段不常見的聖經經文並給予80字內啟示。"
        else:
            prompt = f"Time:{time.time()}。{persona_map[persona]} 針對用戶『{mood_input if mood_input else '疲累但充滿希望'}』的心情，推薦一首優美的基督教詩歌（包含歌名與一段感人歌詞），並給予暖心分析。總字數80字內。"

        res = model.generate_content(prompt)
        if res and res.text:
            header = "【AI經文推送】" if content_type == "聖經經文" else "【AI詩歌推薦】"
            line_api.broadcast(TextSendMessage(text=f"{header}\n\n{res.text}"))
            add_log(f"AI {content_type}廣播成功")
            st.toast("✨ 廣播完成")
    except Exception as e:
        if "429" in str(e):
            st.warning("🛑 衛星配額冷卻中，請明日再試或改用手動。")
            add_log("API 配額封鎖")
        else: st.error("衛星對接失敗")

# 📡 系統日誌
st.markdown("---")
if st.session_state.sys_log:
    st.markdown(f"<pre class='log-box'>{chr(10).join(st.session_state.sys_log)}</pre>", unsafe_allow_html=True)
