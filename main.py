import streamlit as st
import google.generativeai as genai
from datetime import datetime
import random
import time

# --- 1. 頁面配置與 80% 寬度鎖定 CSS ---
st.set_page_config(page_title="聖經控制台 V10.8", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

# 注入 CSS：將網頁內容控制在 80% 寬度，並保持置中
st.markdown("""
    <style>
    /* 核心外框比例控制 */
    @media (min-width: 1024px) {
        .main .block-container {
            max-width: 80% !important;
            padding-left: 5rem !important;
            padding-right: 5rem !important;
        }
    }
    /* 手機端維持滿版以利操作 */
    @media (max-width: 1023px) {
        .main .block-container {
            max-width: 100% !important;
            padding: 0.8rem 0.8rem !important;
        }
    }
    h1 { font-size: 1.5rem !important; margin: 0 !important; color: #E0E0E0; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.2rem; font-weight: bold; }
    [data-testid="stHeader"], footer, #MainMenu { visibility: hidden; height: 0; }
    .log-box { font-size: 0.75rem; background: #121212; color: #00FF41; padding: 12px; border-radius: 8px; font-family: monospace; border: 1px solid #333; }
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
    if len(st.session_state.sys_log) > 5: st.session_state.sys_log.pop()

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

# --- 3. UI 介面 ---
st.title("🛡️ 聖經任務控制台 V10.8")
st.caption(f"📅 {datetime.now().strftime('%m/%d')} | 🛰️ 80% 比例視覺鎖定模式 | v10.8")

# 即時廣播
from linebot.models import TextSendMessage
with st.form("broadcast_form", clear_on_submit=True):
    st.subheader("✍️ 即時廣播傳輸")
    custom_text = st.text_area("內容：", placeholder="在此輸入...", label_visibility="collapsed", height=100)
    if st.form_submit_button("📢 執行全員廣播"):
        if custom_text.strip():
            try:
                line_api.broadcast(TextSendMessage(text=f"【特別推送】\n\n{custom_text}"))
                add_log("廣播發送成功")
                st.toast("✅ 廣播已發送")
            except Exception as e:
                st.error("傳輸異常")

st.markdown("---")

# AI 智慧廣播 (保留 V10.7 流量防護邏輯)
st.subheader("🤖 AI 智慧廣播")
mood_input = st.text_input("今日心情：", placeholder="例如：挑戰、疲累...")
persona = st.selectbox("風格：", ["溫暖啟發 (暖心)", "冷靜理性 (專業)", "K.I.T.T. 霹靂語調"], index=0)

if st.button("✨ 啟動 AI 廣播推送"):
    status = st.empty()
    try:
        status.info("🔍 雷達掃描衛星頻道中...")
        all_models = [m.name for m in genai.list_models()]
        flash_models = [n for n in all_models if 'flash' in n]
        target_model = flash_models[0] if flash_models else all_models[0]
        add_log(f"鎖定頻道: {target_model[-15:]}")
        
        persona_map = {
            "溫暖啟發 (暖心)": "你是溫柔牧者，語氣鼓勵。",
            "冷靜理性 (專業)": "你是專業分析師，語氣簡練。",
            "K.I.T.T. 霹靂語調": "你是K.I.T.T.，語氣冷靜專業，稱呼Brett。"
        }
        
        model = genai.GenerativeModel(target_model)
        prompt = f"{persona_map[persona]} 針對『{mood_input if mood_input else '隨機信仰力量'}』選經文並給予80字內啟示。隨機ID:{random.random()}"

        res = None
        for attempt in range(2):
            try:
                status.info(f"🤖 AI 生成中... (嘗試 {attempt+1}/2)")
                res = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.9))
                break 
            except Exception as e:
                if "429" in str(e) and attempt == 0:
                    status.warning("⚠️ 衛星頻寬塞車，自動重試中...")
                    time.sleep(5)
                    continue
                raise e

        if res and hasattr(res, 'text'):
            status.info("📢 正在廣播...")
            line_api.broadcast(TextSendMessage(text=f"【AI智慧推送】\n\n{res.text}"))
            add_log(f"AI 推送達成")
            status.success("✨ 任務圓滿達成")
        else:
            status.error("AI 內容生成異常")

    except Exception as e:
        err = str(e)
        if "429" in err:
            status.error("🛑 流量上限！請稍後 1 分鐘再試。")
            add_log("警告：流量封鎖")
        else:
            status.error(f"衛星對接失敗：{err[:20]}")
            add_log(f"錯誤: {err[:20]}")

st.markdown("---")
st.subheader("📡 系統運行日誌")
if st.session_state.sys_log:
    st.markdown(f"<pre class='log-box'>{chr(10).join(st.session_state.sys_log)}</pre>", unsafe_allow_html=True)
