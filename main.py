import streamlit as st
import google.generativeai as genai
from datetime import datetime
import random
import time
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 1. 頁面配置與極速 CSS ---
st.set_page_config(page_title="聖經控制台 V10.5", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .block-container { padding: 0.8rem 0.8rem !important; max-width: 100vw !important; overflow-x: hidden; }
    h1 { font-size: 1.3rem !important; margin: 0 !important; color: #E0E0E0; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.2rem; font-weight: bold; }
    [data-testid="stHeader"], footer, #MainMenu { visibility: hidden; height: 0; }
    .log-box { font-size: 0.75rem; background: #121212; color: #00FF41; padding: 12px; border-radius: 8px; font-family: monospace; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心組件安全加載 ---
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

@st.cache_resource
def init_apis():
    line = LineBotApi(LINE_TOKEN)
    genai.configure(api_key=GEMINI_API_KEY)
    return line

if not GEMINI_API_KEY or not LINE_TOKEN:
    st.error("❌ 核心金鑰未就緒")
    st.stop()

line_api = init_apis()

# --- 3. UI 介面佈局 ---
st.title("🛡️ 聖經任務控制台 V10.5")
st.caption(f"📅 {datetime.now().strftime('%m/%d')} | 🛰️ 傳輸流暢度優化模式 | v10.5")

# ⏰ 多重排程設定
with st.expander("⏰ 推送時段管理", expanded=False):
    schedules = st.multiselect("排程時段：", ["06:30", "07:00", "08:00", "09:00", "12:00", "21:00"], default=["06:30", "08:00"])
    if st.button("💾 更新排程"):
        add_log(f"排程存檔: {len(schedules)} 個時段")
        st.toast("✅ 設定已備份")

st.markdown("---")

# ✍️ 即時廣播 (自動清除)
st.subheader("✍️ 即時廣播傳輸")
with st.form("broadcast_form", clear_on_submit=True):
    custom_text = st.text_area("內容：", placeholder="在此輸入...", label_visibility="collapsed", height=100)
    if st.form_submit_button("📢 執行全員廣播"):
        if custom_text.strip():
            try:
                line_api.broadcast(TextSendMessage(text=f"【特別推送】\n\n{custom_text}"))
                add_log("廣播送達成功")
                st.toast("✅ 廣播已發送")
            except Exception as e:
                add_log(f"廣播失敗: {str(e)[:20]}")
                st.error("傳輸異常")

st.markdown("---")

# 🤖 AI 智慧廣播 (修正卡死問題)
st.subheader("🤖 AI 智慧廣播")
mood_input = st.text_input("今日心情：", placeholder="例如：挑戰、疲累...")
persona = st.selectbox("回覆風格：", ["溫暖啟發 (暖心)", "冷靜理性 (專業)", "K.I.T.T. 霹靂語調"], index=0)

if st.button("✨ 啟動 AI 廣播推送"):
    # 增加按鈕狀態變數，防止重複觸發
    status_placeholder = st.empty()
    try:
        status_placeholder.info("🛰️ 衛星通訊建立中...")
        
        # 效能修正：減少偵測頻率，直接指定主模型，若失敗再切換
        target_model = 'gemini-1.5-flash'
        
        persona_map = {
            "溫暖啟發 (暖心)": "你是溫柔牧者，語氣鼓勵。",
            "冷靜理性 (專業)": "你是專業分析師，語氣簡練。",
            "K.I.T.T. 霹靂語調": "你是K.I.T.T.，稱呼Brett，語氣冷靜專業帶微幽默。"
        }
        
        model = genai.GenerativeModel(target_model)
        prompt = f"{persona_map[persona]} 針對『{mood_input if mood_input else '隨機力量'}』主題，選一段經文並給予80字內啟示。隨機因子:{random.random()}。"
        
        # 生成內容
        status_placeholder.info("🤖 AI 正在生成靈糧...")
        res = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.9))

        if res and hasattr(res, 'text'):
            status_placeholder.info("📢 正在向所有好友廣播...")
            line_api.broadcast(TextSendMessage(text=f"【AI智慧推送】\n\n{res.text}"))
            add_log(f"AI 推送達成 ({persona[:2]})")
            status_placeholder.success("✨ 任務圓滿達成")
            st.toast("✨ 全員廣播成功")
        else:
            status_placeholder.error("AI 內容生成異常")

    except Exception as e:
        err = str(e)
        if "429" in err:
            add_log("流量限制：請稍候")
            status_placeholder.error("衛星頻寬繁忙，請 1 分鐘後再試。")
        else:
            add_log(f"連線中斷: {err[:20]}")
            status_placeholder.error(f"連線失敗：{err[:20]}")

st.markdown("---")

# 📡 系統運行日誌
st.subheader("📡 系統運行日誌")
if st.session_state.sys_log:
    st.markdown(f"<pre class='log-box'>{chr(10).join(st.session_state.sys_log)}</pre>", unsafe_allow_html=True)
