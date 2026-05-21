import streamlit as st
import google.generativeai as genai
from datetime import datetime, timedelta, timezone
import random
import time
import threading

# --- 1. 頁面配置 (極致一頁式無捲頁) ---
st.set_page_config(page_title="聖經控制台 V15.2", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

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

# --- 2. 核心配置 ---
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

# --- 3. 不滅全域守護引擎 (V15.2 結構精煉與時間鎖版) ---
@st.cache_resource
class GlobalAutomatonEngine:
    def __init__(self):
        # 修正 3：排程管理預設時間調整為 09:00
        self.schedule = "09:00"
        self.completed_tasks = {}
        self.logs = ["📡 系統提示：V15.2 九點定錨與反思領受鎖定核心已就位。"]
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
                    if date_today not in self.completed_tasks:
                        self.completed_tasks[date_today] = []
                    
                    should_trigger = False
                    if now_str in schedules and now_str not in self.completed_tasks[date_today]:
                        self.completed_tasks[date_today].append(now_str)
                        should_trigger = True

                if should_trigger:
                    time.sleep(random.uniform(1.0, 3.0))
                    try:
                        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
                        
                        # 修正 1：Prompt 結構精煉為三行
                        prompt = (
                            f"現在的時間點是 {now_str}。你是溫柔牧者，請為這個特定的時刻精選一段聖經經文，並給予深度的反思與領受。\n\n"
                            f"【輸出嚴格格式要求】：\n"
                            f"1. 第一行必須明確寫出【經文章節】，例如：(約翰福音 3:16) 或 (詩篇 23:1)\n"
                            f"2. 第二行寫出完整的【經文內容】\n"
                            f"3. 第三行寫出【今日反思與領受】，引導讀者如何將這段經文的啟示應用在今天的日常生活中。\n"
                            f"4. 直接輸出純文字，不要使用任何 ** 粗體符號或 # 標題符號。\n"
                            f"5. 【關鍵防線】：敘述長度不設限，但全文必須在一個完整的「句號」處優雅結束，絕對不可在句子中途斷掉。"
                        )
                        
                        res = model.generate_content(
                            prompt,
                            generation_config=genai.types.GenerationConfig(
                                temperature=0.75, top_p=0.90, max_output_tokens=2000
                            )
                        )
                        
                        if res and res.text:
                            safe_text = str(res.text).strip()
                            line_api.broadcast(TextSendMessage(text=f"【自動排程推送】\n\n{safe_text}"))
                            self.add_log(f"自動排程推送成功 ({now_str})")
                        else:
                            with self.lock:
                                if now_str in self.completed_tasks[date_today]:
                                    self.completed_tasks[date_today].remove(now_str)
                    except Exception as inner_err:
                        with self.lock:
                            if now_str in self.completed_tasks[date_today]:
                                    self.completed_tasks[date_today].remove(now_str)
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

# --- 4. UI 佈局 ---
st.markdown(f"<h1>🛡️ 聖經任務控制台+LINE推送 V15.2 <span class='status-tag'>🛰️ 衛星通訊正常</span></h1>", unsafe_allow_html=True)
st.caption(f"📅 {datetime.now(TZ_TW).strftime('%m/%d')} | 🚀 結構精煉定錨版")

# ⏰ 排程管理
# 修正 3：排程管理提示字改為 (預設 9:00)
with st.expander("⏰ 排程管理 (預設 9:00)", expanded=False):
    with engine.lock:
        current_schedule_val = engine.schedule
    schedule_input = st.text_input("24h 時段：", value=current_schedule_val, label_visibility="collapsed")
    if st.button("💾 保存並同步引擎"):
        with engine.lock:
            engine.schedule = schedule_input
        engine.add_log(f"排程更新: {schedule_input[:15]}")
        # 修正 2：彈出提示文字改成「預設時段已更新」
        st.toast("✅ 預設時段已更新")

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
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
        persona_map = {"暖心": "溫柔牧者。", "專業": "分析師。", "KITT": "KITT，稱呼Brett。"}
        
        # 修正 1：手動 AI 智慧廣播 Prompt 同步改為三行全新結構
        if content_type == "聖經經文":
            prompt = (
                f"{persona_map[persona]} 針對『{mood_input if mood_input else '信仰'}』精選一段聖經經文，並給予深度的反思與領受。\n\n"
                f"【輸出嚴格格式要求】\n"
                f"1. 第一行必須寫出明確的【經文章節】，例如：(約翰福音 3:16)\n"
                f"2. 第二行寫出完整的【經文內容】\n"
                f"3. 第三行寫出【今日反思與領受】。\n"
                f"4. 直接輸出純文字，不要使用粗體或標題符號。結構必須絕對完整結尾。"
            )
        else:
            prompt = (
                f"{persona_map[persona]} 針對用戶『{mood_input if mood_input else '疲累'}』的心情推薦基督教詩歌(含歌名歌詞)與深度分析。\n\n"
                f"【輸出嚴格格式要求】\n"
                f"1. 必須明確寫出【詩歌歌名】與【精選歌詞內容】\n"
                f"2. 第二行提供溫暖的【附註說明與分析】\n"
                f"3. 第三行提供一段專屬的【心靈領受與祝福】\n"
                f"4. 直接輸出純文字，不要使用粗體或標題符號。結構必須絕對完整結尾。"
            )
        
        res = model.generate_content(
            prompt, 
            generation_config=genai.types.GenerationConfig(
                temperature=0.75, top_p=0.90, max_output_tokens=2000
            )
        )
        if res and res.text:
            safe_text_manual = str(res.text).strip()
            header = "【AI經文推送】" if content_type == "聖經經文" else "【AI詩歌推薦】"
            line_api.broadcast(TextSendMessage(text=f"{header}\n\n{safe_text_manual}"))
            engine.add_log(f"手動觸發 AI {content_type[:2]}成功")
            st.toast("✨ 廣播完成")
    except Exception as e:
        st.error(f"衛星對接失敗: {str(e)[:40]}")
        engine.add_log(f"AI廣播失敗: {str(e)[:35]}")

st.markdown("---")
with engine.lock:
    current_logs = list(engine.logs)
if current_logs:
    st.markdown(f"<pre class='log-box'>{chr(10).join(current_logs)}</pre>", unsafe_allow_html=True)
