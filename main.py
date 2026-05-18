import streamlit as st
import google.generativeai as genai
from datetime import datetime, timedelta, timezone
import random
import time
import threading

# --- 1. 頁面配置 (極致校準一頁式) ---
st.set_page_config(page_title="聖經控制台 V12.8", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .main .block-container { max-width: 80% !important; padding: 0.3rem 1rem !important; overflow: hidden !important; }
    @media (max-width: 1023px) { .main .block-container { max-width: 100% !important; padding: 0.3rem !important; } }
    h1 { font-size: 1.15rem !important; margin: 0 !important; line-height: 1.1 !important; color: #E0E0E0; }
    .stTextArea>div>div>textarea { height: 50px !important; border-radius: 8px; }
    .stTextInput>div>div>input { height: 2.1rem !important; border-radius: 8px; }
    .stSelectbox>div>div { height: 2.1rem !important; font-size: 13px !important; display: flex; align-items: center; }
    .stButton>button { border-radius: 8px; height: 2.5rem; font-weight: bold; }
    .log-box { font-size: 0.65rem; background: #121212; color: #00FF41; padding: 6px; border-radius: 8px; font-family: monospace; height: 60px; overflow-y: auto; border: 1px solid #333; }
    .status-tag { font-size: 0.7rem; padding: 2px 8px; border-radius: 10px; background: #2E7D32; color: white; margin-left: 10px; }
    [data-testid="stHeader"], footer, #MainMenu { visibility: hidden; height: 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心組件與時區 ---
def get_cfg(key, fallback):
    try: return st.secrets.get(key, fallback) or fallback
    except: return fallback

GEMINI_API_KEY = get_cfg("GEMINI_API_KEY", "")
LINE_TOKEN = get_cfg("LINE_ACCESS_TOKEN", "")
TZ_TW = timezone(timedelta(hours=8))

# 🎯 填入位置：將您找到的 ID 複製，黏貼替換掉下方的字串
CONTACT_BOOK = {
    "請選擇聯絡人...": "",
    "Brett (我自己)": "填入您的User_ID", 
    "重要好友 A": "填入好友_A_的ID",
    "重要好友 B": "填入好友_B_的ID"
}

@st.cache_resource
def get_global_engine_assets():
    return {
        "schedule": "08:00, 12:00, 21:00", 
        "last_run": "", 
        "engine_active": False,
        "logs": ["系統引導：請讓好友發送訊息給機器人，ID將會在此攔截顯示。"],
        "lock": threading.Lock()
    }

global_data = get_global_engine_assets()

def add_global_log(msg):
    with global_data["lock"]:
        ts = datetime.now(TZ_TW).strftime("%H:%M:%S")
        global_data["logs"].insert(0, f"[{ts}] {msg}")
        if len(global_data["logs"]) > 4: global_data["logs"].pop()

from linebot import LineBotApi
from linebot.models import TextSendMessage
line_api = LineBotApi(LINE_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. 自動推送與 Webhook 攔截模擬 ---
def auto_push_worker():
    while True:
        try:
            with global_data["lock"]: global_data["engine_active"] = True
            now_tw = datetime.now(TZ_TW)
            now_str = now_tw.strftime("%H:%M")
            date_str = now_tw.strftime("%Y-%m-%d")
            task_id = f"{date_str}-{now_str}"
            
            with global_data["lock"]: current_schedule = global_data["schedule"]
            schedules = [s.strip() for s in current_schedule.split(",")]
            
            if now_str in schedules and global_data["last_run"] != task_id:
                try:
                    models = [m.name for m in genai.list_models()]
                    target_model = next((n for n in models if 'flash' in n), models[0])
                    model = genai.GenerativeModel(target_model)
                    
                    salt = random.randint(1000, 9999)
                    prompt = f"Seed:{time.time()}-{salt}。當前時間點是 {now_str}。你是溫柔牧者，請為這個特定時段精選一段聖經經文並給予80字內溫暖啟示。"
                    res = model.generate_content(prompt, generation_config={"temperature": 0.95, "top_p": 0.95, "max_output_tokens": 150})
                    
                    if res and res.text:
                        line_api.broadcast(TextSendMessage(text=f"【自動排程推送】\n\n{res.text}"))
                        global_data["last_run"] = task_id
                        add_global_log(f"自動推送成功 ({now_str})")
                except Exception as api_err:
                    add_global_log(f"API異常: {str(api_err)[:15]}")
        except Exception: pass
        time.sleep(30)

with global_data["lock"]:
    threads = threading.enumerate()
    if not any(t.name == "KITT_AutoEngine" for t in threads):
        engine_thread = threading.Thread(target=auto_push_worker, name="KITT_AutoEngine", daemon=True)
        engine_thread.start()
        global_data["engine_active"] = True

# --- 4. UI 佈局 ---
with global_data["lock"]: is_active = global_data["engine_active"]
status_html = '<span class="status-tag">🛰️ 衛星通訊正常</span>' if is_active else '<span class="status-tag" style="background:#C62828;">❌ 引擎離線</span>'
st.markdown(f"<h1>🛡️ 聖經任務控制台+LINE推送 V12.8 {status_html}</h1>", unsafe_allow_html=True)
st.caption(f"📅 {datetime.now(TZ_TW).strftime('%m/%d')} | 🚀 智慧通訊錄與 ID 攔截雷達版")

# ⏰ 排程管理
with st.expander("⏰ 排程管理 (預設 08:00, 12:00, 21:00)", expanded=False):
    schedule_input = st.text_input("24h 時段：", value=global_data["schedule"], label_visibility="collapsed")
    if st.button("💾 保存並同步引擎"):
        with global_data["lock"]: global_data["schedule"] = schedule_input
        add_global_log(f"排程更新: {schedule_input[:15]}")
        st.toast("✅ 預設三時段已更新")

# ✍️ 手動廣播
st.subheader("✍️ 手動廣播")
with st.form("manual_form", clear_on_submit=False):
    mc1, mc2 = st.columns([1, 2])
    with mc1:
        target_type = st.selectbox("對象：", ["全員廣播", "指定單人"], index=0, label_visibility="collapsed")
    with mc2:
        if target_type == "全員廣播":
            st.selectbox("通訊錄已鎖定", ["(全員發送模式)"], disabled=True, label_visibility="collapsed")
            selected_id = ""
            selected_name = "全員"
        else:
            contact_name = st.selectbox("請選擇聯絡人：", list(CONTACT_BOOK.keys()), index=0, label_visibility="collapsed")
            selected_id = CONTACT_BOOK[contact_name]
            selected_name = contact_name
    
    custom_text = st.text_area("廣播內容：", placeholder="在此輸入文字或歌曲連結...", label_visibility="collapsed")
    
    if st.form_submit_button("📢 執行發送"):
        if custom_text.strip():
            try:
                msg_obj = TextSendMessage(text=f"【手動推送】\n\n{custom_text}")
                if target_type == "全員廣播":
                    line_api.broadcast(msg_obj)
                    add_global_log("全員廣播完成")
                    st.toast("✅ 已送達所有人")
                else:
                    if selected_id and "填入" not in selected_id:
                        line_api.push_message(selected_id, msg_obj)
                        add_global_log(f"單人推送 -> {selected_name}")
                        st.toast(f"🎯 已定向送達 {selected_name}")
                    else:
                        st.error("❌ 錯誤：請選擇已填入有效 ID 的聯絡人！")
            except Exception: 
                st.error("傳輸中斷，請檢查通訊錄 ID 配置")
                add_global_log("手動傳輸失敗")

st.markdown("---")
# 🤖 AI 智慧廣播
st.subheader("🤖 AI 智慧廣播")
c1, c2, c3 = st.columns([1, 1, 1])
with c1: mood_input = st.text_input("心情：", label_visibility="collapsed")
with c2: persona = st.selectbox("風格：", ["暖心", "專業", "KITT"], label_visibility="collapsed")
with c3: content_type = st.selectbox("內容：", ["聖經經文", "推薦詩歌"], label_visibility="collapsed")

if st.button("✨ 啟動 AI 廣播"):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        persona_map = {"暖心": "溫柔牧者。", "專業": "分析師。", "KITT": "KITT，稱呼Brett。"}
        salt = random.randint(1000, 9999)
        prompt = f"Seed:{time.time()}-{salt}。{persona_map[persona]} 針對『{mood_input if mood_input else '信仰'}』給予啟示。80字內。"
        res = model.generate_content(prompt, generation_config={"temperature": 0.95, "top_p": 0.95})
        if res and res.text:
            header = "【AI經文推送】" if content_type == "聖經經文" else "【AI詩歌推薦】"
            line_api.broadcast(TextSendMessage(text=f"{header}\n\n{res.text}"))
            add_global_log("AI手動發送成功")
            st.toast("✨ 已送達")
    except Exception: st.error("衛星對接失敗")

st.markdown("---")
with global_data["lock"]: current_logs = list(global_data["logs"])
if current_logs:
    st.markdown(f"<pre class='log-box'>{chr(10).join(current_logs)}</pre>", unsafe_allow_html=True)
