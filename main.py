import streamlit as st
import google.generativeai as genai
from datetime import datetime, timedelta, timezone
import random
import time
import threading

# --- 1. 頁面配置 (極致一頁式無捲頁) ---
st.set_page_config(page_title="聖經控制台 V13.1", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .main .block-container { max-width: 80% !important; padding: 0.3rem 1rem !important; overflow: hidden !important; }
    @media (max-width: 1023px) { .main .block-container { max-width: 100% !important; padding: 0.3rem !important; } }
    h1 { font-size: 1.15rem !important; margin: 0 !important; line-height: 1.1 !important; color: #E0E0E0; }
    .stTextArea>div>div>textarea { height: 55px !important; border-radius: 8px; }
    .stTextInput>div>div>input { height: 2.1rem !important; border-radius: 8px; }
    .stButton>button { border-radius: 8px; height: 2.5rem; font-weight: bold; }
    .log-box { font-size: 0.65rem; background: #121212; color: #00FF41; padding: 6px; border-radius: 8px; font-family: monospace; height: 65px; overflow-y: auto; border: 1px solid #333; }
    .status-tag { font-size: 0.7rem; padding: 2px 8px; border-radius: 10px; background: #2E7D32; color: white; margin-left: 10px; }
    [data-testid="stHeader"], footer, #MainMenu { visibility: hidden; height: 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心配置與時區鎖定 ---
def get_cfg(key, fallback):
    try: return st.secrets.get(key, fallback) or fallback
    except: return fallback

GEMINI_API_KEY = get_cfg("GEMINI_API_KEY", "")
LINE_TOKEN = get_cfg("LINE_ACCESS_TOKEN", "")
TZ_TW = timezone(timedelta(hours=8))

from linebot import LineBotApi
from linebot.models import TextSendMessage
line_api = LineBotApi(LINE_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. 動力核心：不滅全域守護引擎 (V13.1 固態防禦版) ---
@st.cache_resource
class GlobalAutomatonEngine:
    """將背景巡航線程直接升級為雲端級不滅組件"""
    def __init__(self):
        self.schedule = "08:00, 12:00, 21:00"
        self.last_run_date_hour = "" # 紀錄最後執行的 日期-小時-分鐘 防止重複
        self.logs = ["📡 系統提示：V13.1 終極固態防禦核心已全面接管防線。"]
        self.lock = threading.Lock()
        
        self.thread = threading.Thread(target=self._patrol_loop, name="KITT_EternalEngine", daemon=True)
        self.thread.start()

    def _patrol_loop(self):
        while True:
            try:
                now_tw = datetime.now(TZ_TW)
                now_str = now_tw.strftime("%H:%M")
                date_today = now_tw.strftime("%Y-%m-%d")
                
                with self.lock:
                    schedules = [s.strip() for s in self.schedule.split(",")]
                
                # 優化：增加時間寬容度檢查（若在排程時間或後一分鐘內，且今天該時段未跑過）
                # 這能完美防止因 25 秒循環與伺服器網路微小延遲導致的「錯過準點」Bug
                matched_schedule = None
                for s in schedules:
                    try:
                        sched_time = datetime.strptime(s, "%H:%M")
                        # 允許準點或最多延遲 1 分鐘內進行補發觸發
                        diff = (datetime.strptime(now_str, "%H:%M") - sched_time).total_seconds()
                        if 0 <= diff <= 60:
                            matched_schedule = s
                            break
                    except:
                        pass
                
                task_id = f"{date_today}-{matched_schedule}" if matched_schedule else ""
                
                if matched_schedule and self.last_run_date_hour != task_id:
                    # 修正漏洞 1：放棄脆弱的 list_models() 權限探測，硬鎖定業界最穩定的核心型號
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    
                    salt = random.randint(1000, 9999)
                    prompt = f"Seed:{time.time()}-{salt}。當前時間段是 {matched_schedule}。你是溫柔牧者，請為這個特定的時刻精選一段聖經經文（確保每次內容完全不同），並給予80字內溫暖啟示。直接輸出內容。"
                    
                    res = model.generate_content(
                        prompt,
                        generation_config={
                            "temperature": 0.95,
                            "top_p": 0.95,
                            "max_output_tokens": 150
                        }
                    )
                    
                    if res and res.text:
                        line_api.broadcast(TextSendMessage(text=f"【自動排程推送】\n\n{res.text}"))
                        self.last_run_date_hour = task_id # 任務鎖定
                        self.add_log(f"自動排程推送成功 ({matched_schedule})")
            except Exception as e:
                # 即使某一發 API 失敗，例外隔離機制也會確保主循環不崩潰，下一秒繼續巡邏
                pass
            time.sleep(25)

    def add_log(self, msg):
        with self.lock:
            ts = datetime.now(TZ_TW).strftime("%H:%M:%S")
            self.logs.insert(0, f"[{ts}] {msg}")
            if len(self.logs) > 4: self.logs.pop()

# 獲取全域唯一引擎實例
engine = GlobalAutomatonEngine()

# --- 4. UI 佈局 ---
st.markdown(f"<h1>🛡️ 聖經任務控制台+LINE推送 V13.1 <span class='status-tag'>🛰️ 衛星通訊正常</span></h1>", unsafe_allow_html=True)
st.caption(f"📅 {datetime.now(TZ_TW).strftime('%m/%d')} | 🚀 固態硬體防禦模式鎖定")

# ⏰ 排程管理
with st.expander("⏰ 排程管理 (預設 08:00, 12:00, 21:00)", expanded=False):
    with engine.lock:
        current_schedule_val = engine.schedule
    schedule_input = st.text_input("24h 時段：", value=current_schedule_val, label_visibility="collapsed")
    if st.button("💾 保存並同步引擎"):
        with engine.lock:
            engine.schedule = schedule_input
        engine.add_log(f"排程更新: {schedule_input[:15]}")
        st.toast("✅ 預設三時段已成功同步至全域引擎")

# ✍️ 手動廣播
st.subheader("✍️ 手動全員廣播")
with st.form("manual_form", clear_on_submit=False):
    custom_text = st.text_area("內容：", placeholder="在此輸入要廣播給所有好友的文字或歌曲連結...", label_visibility="collapsed")
    if st.form_submit_button("📢 執行全員廣播"):
        if custom_text.strip():
            try:
                line_api.broadcast(TextSendMessage(text=f"【手動推送】\n\n{custom_text}"))
                engine.add_log("手動全員廣播完成")
                st.toast("✅ 已送達所有好友")
            except Exception:
                st.error("連線異常，請檢查 LINE Token")

st.markdown("---")

# 🤖 AI 智慧廣播
st.subheader("🤖 AI 智慧廣播")
c1, c2, c3 = st.columns([1, 1, 1])
with c1: mood_input = st.text_input("心情：", placeholder="心情...", label_visibility="collapsed")
with c2: persona = st.selectbox("風格：", ["暖心", "專業", "KITT"], label_visibility="collapsed")
with c3: content_type = st.selectbox("內容：", ["聖經經文", "推薦詩歌"], label_visibility="collapsed")

if st.button("✨ 啟動 AI 廣播"):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        persona_map = {"暖心": "溫柔牧者。", "專業": "分析師。", "KITT": "KITT，稱呼Brett。"}
        salt = random.randint(1000, 9999)
        
        if content_type == "聖經經文":
            prompt = f"Seed:{time.time()}-{salt}。{persona_map[persona]} 針對『{mood_input if mood_input else '信仰'}』給予聖經經文啟示。80字內。"
        else:
            prompt = f"Seed:{time.time()}-{salt}。{persona_map[persona]} 針對用戶『{mood_input if mood_input else '疲累'}』的心情推薦基督教詩歌(含歌名歌詞)與暖心分析。80字內。"
            
        res = model.generate_content(prompt, generation_config={"temperature": 0.95, "top_p": 0.95})
        if res and res.text:
            header = "【AI經文推送】" if content_type == "聖經經文" else "【AI詩歌推薦】"
            line_api.broadcast(TextSendMessage(text=f"{header}\n\n{res.text}"))
            engine.add_log(f"手動觸發 AI {content_type[:2]}成功")
            st.toast("✨ 廣播完成")
    except Exception:
        st.error("衛星對接失敗")

st.markdown("---")
with engine.lock:
    current_logs = list(engine.logs)

if current_logs:
    st.markdown(f"<pre class='log-box'>{chr(10).join(current_logs)}</pre>", unsafe_allow_html=True)
