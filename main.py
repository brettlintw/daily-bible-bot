import streamlit as st
import google.generativeai as genai
from datetime import datetime
import random
import time

# --- 1. 頁面配置 (極致壓縮一頁式) ---
st.set_page_config(page_title="聖經任務控制台 V11.6", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

# 注入 CSS：強制鎖定 80% 寬度，消除溢出捲軸，極小化間距
st.markdown("""
    <style>
    /* 核心佈局比例與捲軸封鎖 */
    .main .block-container {
        max-width: 80% !important;
        padding: 0.3rem 1rem !important;
        overflow: hidden !important;
    }
    @media (max-width: 1023px) { .main .block-container { max-width: 100% !important; padding: 0.3rem !important; } }
    
    /* 標題與文字緊湊化 */
    h1 { font-size: 1.2rem !important; margin: 0 !important; line-height: 1.1 !important; color: #E0E0E0; }
    h3 { font-size: 0.85rem !important; margin: 0.1rem 0 !important; font-weight: bold; }
    .stCaption { font-size: 0.7rem !important; margin-bottom: 0.2rem !important; }
    hr { margin: 0.3rem 0 !important; }
    
    /* 組件高度精確控制 */
    .stTextArea>div>div>textarea { height: 55px !important; border-radius: 8px; font-size: 14px !important; }
    .stTextInput>div>div>input { height: 1.8rem !important; border-radius: 8px; font-size: 14px !important; }
    .stButton>button { border-radius: 8px; height: 2.4rem; font-weight: bold; font-size: 14px !important; }
    .stSelectbox>div>div { height: 1.8rem !important; font-size: 13px !important; }
    
    /* 摺疊選單緊湊化 */
    .stExpander { border: none !important; box-shadow: none !important; }
    
    /* 日誌區高度鎖定 */
    .log-box { 
        font-size: 0.65rem; background: #121212; color: #00FF41; 
        padding: 6px; border-radius: 8px; font-family: monospace; 
        border: 1px solid #333; height: 65px; overflow-y: auto;
    }
    [data-testid="stHeader"], footer, #MainMenu { visibility: hidden; height: 0; }
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
    if len(st.session_state.sys_log) > 3: st.session_state.sys_log.pop()

from linebot import LineBotApi
from linebot.models import TextSendMessage
line_api = LineBotApi(LINE_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. UI 佈局 ---
st.title("🛡️ 聖經任務控制台+LINE推送 V11.6")
st.caption(f"📅 {datetime.now().strftime('%m/%d')} | 🛰️ 一頁式極致壓縮模式")

# ⏰ 排程管理 (摺疊式以節省空間)
with st.expander("⏰ 推送排程設定", expanded=False):
    custom_schedules = st.text_input("24h 時段 (用逗號隔開)：", value="06:30, 08:00, 12:00, 21:00", label_visibility="collapsed")
    if st.button("💾 保存排程"):
        add_log(f"排程存檔: {custom_schedules[:15]}...")
        st.toast("✅ 已保存")

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

# 🤖 AI 智慧廣播 (雙模切換)
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
        
        persona_map = {"暖心": "溫柔牧者。", "專業": "專業分析師。", "KITT": "KITT，稱呼Brett。"}
        
        if content_type == "聖經經文":
            prompt = f"Time:{time.time()}。{persona_map[persona]} 針對『{mood_input if mood_input else '信仰'}』選經文並給予80字內啟示。"
        else:
            prompt = f"Time:{time.time()}。{persona_map[persona]} 針對用戶『{mood_input if mood_input else '疲累'}』推薦詩歌(含歌名歌詞)與暖心分析。80字內。"

        res = model.generate_content(prompt)
        if res and res.text:
            header = "【AI經文推送】" if content_type == "聖經經文" else "【AI詩歌推薦】"
            line_api.broadcast(TextSendMessage(text=f"{header}\n\n{res.text}"))
            add_log(f"AI {content_type[:2]}成功")
            st.toast("✨ 廣播完成")
    except Exception as e:
        if "429" in str(e):
            st.warning("衛星冷卻中，請等 60 秒。")
            add_log("配額上限")
        else: st.error("對接失敗")

# 📡 系統日誌
st.markdown("---")
if st.session_state.sys_log:
    st.markdown(f"<pre class='log-box'>{chr(10).join(st.session_state.sys_log)}</pre>", unsafe_allow_html=True)
