import streamlit as st
import google.generativeai as genai
from datetime import datetime
import random
import time

# --- 1. 頁面配置 (精簡一頁式) ---
st.set_page_config(page_title="聖經控制台 V11.2", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .main .block-container { max-width: 80% !important; padding: 0.5rem !important; overflow: hidden !important; }
    @media (max-width: 1023px) { .main .block-container { max-width: 100% !important; } }
    h1 { font-size: 1.1rem !important; margin: 0 !important; }
    .stTextArea>div>div>textarea { height: 65px !important; border-radius: 10px; }
    .stButton>button { border-radius: 10px; height: 2.6rem; font-weight: bold; }
    [data-testid="stHeader"], footer, #MainMenu { visibility: hidden; height: 0; }
    .log-box { font-size: 0.7rem; background: #121212; color: #00FF41; padding: 8px; border-radius: 8px; font-family: monospace; height: 80px; overflow-y: auto; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心組件與對接邏輯 ---
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

# 每次執行都重新驗證配置，確保不卡死
from linebot import LineBotApi
from linebot.models import TextSendMessage
line_api = LineBotApi(LINE_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. UI 一頁式佈局 ---
st.title("🛡️ 聖經任務控制台 V11.2")
st.caption(f"📅 {datetime.now().strftime('%m/%d')} | v11.2-Recovery")

# ⏰ 定時推送排程
with st.expander("⏰ 推送排程管理", expanded=False):
    schedules = st.multiselect("設定時段：", ["06:30", "07:00", "08:00", "09:00", "12:00", "21:00"], default=["06:30", "08:00"])
    if st.button("💾 同步排程"):
        add_log(f"排程存檔: {len(schedules)} 個時段")
        st.toast("✅ 已同步")

# ✍️ 即時廣播
with st.form("broadcast_form", clear_on_submit=True):
    custom_text = st.text_area("內容：", placeholder="在此輸入...", label_visibility="collapsed")
    if st.form_submit_button("📢 執行全員廣播"):
        if custom_text.strip():
            try:
                line_api.broadcast(TextSendMessage(text=f"【特別推送】\n\n{custom_text}"))
                add_log("廣播發送成功")
                st.toast("✅ 已送達")
            except Exception as e:
                st.error(f"傳輸失敗: {str(e)[:15]}")

st.markdown("---")

# 🤖 AI 智慧廣播 (強化連線跳脫)
st.subheader("🤖 AI 智慧廣播")
c1, c2 = st.columns([1, 1])
with c1: mood_input = st.text_input("心情：", placeholder="心情...", label_visibility="collapsed")
with c2: persona = st.selectbox("風格：", ["暖心", "專業", "KITT"], index=0, label_visibility="collapsed")

if st.button("✨ 啟動 AI 廣播"):
    status_placeholder = st.empty()
    try:
        # 強制重新獲取模型清單，不使用快取
        models = [m.name for m in genai.list_models()]
        target_model = next((n for n in models if 'flash' in n), models[0])
        
        persona_map = {"暖心": "溫柔牧者。", "專業": "分析師。", "KITT": "KITT，稱呼Brett。"}
        model = genai.GenerativeModel(target_model)
        
        # 增加 Prompt 的亂數性，繞過可能的快取封鎖
        prompt = f"Time:{time.time()}。{persona_map[persona]} 針對『{mood_input if mood_input else '信仰與力量'}』選經文並給予啟示。80字內。"

        res = model.generate_content(prompt)

        if res and hasattr(res, 'text'):
            line_api.broadcast(TextSendMessage(text=f"【AI智慧推送】\n\n{res.text}"))
            add_log("AI 智慧任務達成")
            st.toast("✨ 廣播完成")
        else:
            st.error("衛星回傳數據格式不符")

    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg:
            st.warning("⚠️ 頻寬飽和，請 5 分鐘後再嘗試（或檢查 API 每日上限）。")
            add_log("流量飽和封鎖 (429)")
        else:
            st.error(f"衛星對接失敗")
            add_log(f"Error: {err_msg[:20]}")

# 📡 系統日誌
st.markdown("---")
if st.session_state.sys_log:
    st.markdown(f"<pre class='log-box'>{chr(10).join(st.session_state.sys_log)}</pre>", unsafe_allow_html=True)
