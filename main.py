import streamlit as st
import google.generativeai as genai
from datetime import datetime, timedelta, timezone
import random
import time
import threading

# --- 1. 頁面配置 (極致一頁式無捲頁) ---
st.set_page_config(page_title="聖經控制台 V13.6", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

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

# --- 3. 雙重核心智慧調度演算法 (修復 404 漏洞) ---
def generate_content_safe(prompt, max_tokens=150):
    """具備極限容錯的雙模型降級發射晶片"""
    # 優先使用高階通用型 pro 模型，避開部分免費帳號對 flash 的 404 限制
    primary_model = "gemini-1.5-pro"
    backup_model = "gemini-pro"
    
    try:
        model = genai.GenerativeModel(model_name=primary_model)
        res = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.95, top_p=0.95, max_output_tokens=max_tokens
            )
        )
        if res and res.text:
            return res.text
    except Exception as e:
        # 如果 1.5-pro 依舊回傳 404，立刻啟動備用防線，切換至絕對通車的經典 pro
        if "404" in str(e) or "not found" in str(e).lower():
            model = genai.GenerativeModel(model_name=backup_model)
            res = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.95, top_p=0.95, max_output_tokens=max_tokens
                )
            )
            if res and res.text:
                return res.text
        raise e
    return None

# --- 4. 不滅全域守護引擎 ---
@st.cache_resource
class GlobalAutomatonEngine:
    def __init__(self):
        self.schedule = "08:00, 12:00, 21:00"
        self.completed_tasks = {}
        self.logs = ["📡 系統提示：V13.6 全地區相容防禦核心已全面對接。"]
        self.lock = threading.Lock()
        
        self.thread = threading.Thread(target=self._patrol_loop, name="KITT_EternalEngine", daemon=True)
        self.thread.start()

    def _patrol_loop(self):
        while True:
            try:
                now_tw = datetime.now(TZ_TW)
                now_str = now_tw.strftime("%H:%M")
                date_today = now_tw.strftime("%Y-%m-%d")
                current_second = now_tw.second
                
                with self.lock:
                    schedules = [s.strip() for s in self.schedule.split(",")]
                    if date_today not in self.completed_tasks:
                        self.completed_tasks = {date_today: []}
                    
                    matched_schedule = None
                    for s in schedules:
                        if s == now_str:
                            matched_schedule = s
                            break
                    
                    should_trigger = False
                    if matched_schedule and current_second < 20:
                        if matched_schedule not in self.completed_tasks[date_today]:
                            self.completed_tasks[date_today].append(matched_schedule)
                            should_trigger = True

                if should_trigger:
                    try:
                        salt = random.randint(1000, 9999)
                        prompt = f"Seed:{time.time()}-{salt}。當前時間點是 {matched_schedule}。你是溫柔牧者，請為這個特定的時刻精選一段聖經經文並給予80字內溫暖啟示。直接輸出內容。"
                        
                        text_output = generate_content_safe(prompt, max_tokens=150)
                        
                        if text_output:
                            line_api.broadcast(TextSendMessage(text=f"【自動排程推送】\n\n{text_output}"))
                            self.add_log(f"自動排程推送成功 ({matched_schedule})")
                        else:
                            with self.lock:
                                if matched_schedule in self.completed_tasks[date_today]:
                                    self.completed_tasks[date_today].remove(matched_schedule)
                    except Exception as inner_err:
                        with self.lock:
                            if matched_schedule in self.completed_tasks[date_today]:
                                    self.completed_tasks[date_today].remove(matched_schedule)
                        self.add_log(f"自動發射異常: {str(inner_err)[:20]}")
                        
            except Exception:
                pass
            time.sleep(15)

    def add_log(self, msg):
        with self.lock:
            ts = datetime.now(TZ_TW).strftime("%H:%M:%S")
            self.logs.insert(0, f"[{ts}] {msg}")
            if len(self.logs) > 4: self.logs.pop()

engine = GlobalAutomatonEngine()

# --- 5. UI 佈局 ---
st.markdown(f"<h1>🛡️ 聖經任務控制台+LINE推送 V13.6 <span class='status-tag'>🛰️ 衛星通訊正常</span></h1>", unsafe_allow_html=True)
st.caption(f"📅 {datetime.now(TZ_TW).strftime('%m/%d')} | 🚀 跨模型調度容錯版")

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
            except Exception as line_err:
                st.error(f"連線異常: {str(line_err)[:20]}")

st.markdown("---")

# 🤖 AI 智慧廣播
st.subheader("🤖 AI 智慧廣播")
c1, c2, c3 = st.columns([1, 1, 1])
with c1: mood_input = st.text_input("心情：", placeholder="心情...", label_visibility="collapsed")
with c2: persona = st.selectbox("風格：", ["暖心", "專業", "KITT"], label_visibility="collapsed")
with c3: content_type = st.selectbox("內容：", ["聖經經文", "推薦詩歌"], label_visibility="collapsed")

if st.button("✨ 啟動 AI 廣播"):
    try:
        persona_map = {"暖心": "溫柔牧者。", "專業": "分析師。", "KITT": "KITT，稱呼Brett。"}
        salt = random.randint(1000, 9999)
        
        if content_type == "聖經經文":
            prompt = f"Seed:{time.time()}-{salt}。{persona_map[persona]} 針對『{mood_input if mood_input else '信仰'}』給予聖經經文啟示。80字內。"
        else:
            prompt = f"Seed:{time.time()}-{salt}。{persona_map[persona]} 針對用戶『{mood_input if mood_input else '疲累'}』的心情推薦基督教詩歌(含歌名歌詞)與暖心分析。80字內。"
        
        # 呼叫雙重容錯發射晶片
        res_text = generate_content_safe(prompt, max_tokens=150)
        
        if res_text:
            header = "【AI經文推送】" if content_type == "聖經經文" else "【AI詩歌推薦】"
            line_api.broadcast(TextSendMessage(text=f"{header}\n\n{res_text}"))
            engine.add_log(f"手動觸發 AI {content_type[:2]}成功")
            st.toast("✨ 廣播完成")
    except Exception as e:
        st.error(f"衛星對接失敗: {str(e)[:30]}")
        engine.add_log(f"AI廣播失敗: {str(e)[:25]}")

st.markdown("---")
with engine.lock:
    current_logs = list(engine.logs)

if current_logs:
    st.markdown(f"<pre class='log-box'>{chr(10).join(current_logs)}</pre>", unsafe_allow_html=True)
