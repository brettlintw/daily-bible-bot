import streamlit as st
import google.generativeai as genai
from datetime import datetime, timedelta, timezone
import random
import time
import threading
import json
import os

# --- 1. 頁面配置 (旗艦一頁式) ---
st.set_page_config(page_title="聖經控制台 V18.3", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .main .block-container { max-width: 80% !important; padding: 0.3rem 1rem !important; }
    @media (max-width: 1023px) { .main .block-container { max-width: 100% !important; padding: 0.3rem !important; } }
    h1 { font-size: 1.15rem !important; margin: 0 !important; line-height: 1.1 !important; color: #E0E0E0; }
    .stTextArea>div>div>textarea { height: 55px !important; border-radius: 8px; }
    .stTextInput>div>div>input { height: 2.1rem !important; border-radius: 8px; }
    .stButton>button { border-radius: 8px; height: 2.5rem; font-weight: bold; }
    .status-tag { font-size: 0.7rem; padding: 2px 8px; border-radius: 10px; background: #2E7D32; color: white; margin-left: 10px; }
    .history-card { background: #1E1E1E; padding: 10px; border-radius: 8px; border-left: 5px solid #0288D1; margin-bottom: 8px; color: #E0E0E0; }
    .type-tag-auto { background: #2E7D32; color: white; padding: 1px 6px; border-radius: 4px; font-size: 0.65rem; }
    .type-tag-manual { background: #C62828; color: white; padding: 1px 6px; border-radius: 4px; font-size: 0.65rem; }
    .type-tag-ai { background: #1565C0; color: white; padding: 1px 6px; border-radius: 4px; font-size: 0.65rem; }
    [data-testid="stHeader"], footer, #MainMenu { visibility: hidden; height: 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心時區常量配置 ---
TZ_TW = timezone(timedelta(hours=8))

def get_cfg(key, fallback):
    try: return st.secrets.get(key, fallback) or fallback
    except: return fallback

GEMINI_API_KEY = get_cfg("GEMINI_API_KEY", "")
LINE_TOKEN = get_cfg("LINE_ACCESS_TOKEN", "")
TRIGGER_KEY = get_cfg("TRIGGER_KEY", "KITT_SECURE_KEY_2026")

from linebot import LineBotApi
from linebot.models import TextSendMessage
line_api = LineBotApi(LINE_TOKEN)

genai.configure(api_key=GEMINI_API_KEY)
DB_FILE = "bible_history.json"
CONFIG_FILE = "engine_config.json"

# --- 3. 配置管理 ---
def load_engine_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {"schedule": "09:00"}

def save_engine_config(config_data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)

def save_to_history(category, content):
    current_tw = datetime.now(timezone.utc).astimezone(TZ_TW)
    date_str = current_tw.strftime("%Y-%m-%d")
    time_str = current_tw.strftime("%H:%M:%S")
    
    new_entry = {
        "id": int(time.time() * 1000),
        "date": date_str,
        "time": time_str,
        "category": category,
        "content": content
    }
    
    lock = threading.Lock()
    with lock:
        data = []
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f: data = json.load(f)
            except: data = []
        data.insert(0, new_entry)
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

# --- 4. 經文生成核心 ---
def execute_ai_bible_generation(custom_mood=None, custom_persona="暖心"):
    model = genai.GenerativeModel(model_name="gemini-2.5-flash")
    current_tw = datetime.now(timezone.utc).astimezone(TZ_TW)
    now_hour = current_tw.hour
    
    if 5 <= now_hour < 11: time_context = "開啟美好一天的早晨時分"
    elif 11 <= now_hour < 16: time_context = "忙碌過後的正午/下午舒壓時分"
    else: time_context = "沉靜安穩的夜晚/睡前時分"
    
    persona_intro = "你是溫柔牧者。"
    if custom_persona == "專業": persona_intro = "你是業界專業分析師。"
    elif custom_persona == "KITT": persona_intro = "你是KITT，稱呼Brett。"
        
    mood_context = f"針對主題或心情『{custom_mood}』" if custom_mood else f"針對{time_context}"
    
    prompt = (
        f"{persona_intro} 請{mood_context}精選一段聖經經文，並給予深度反思與領受。\n\n"
        "【輸出順序格式三階鐵律】：\n"
        "你必須嚴格、完美地依照以下格式規範輸出，每行中間空一行，嚴禁輸出任何額外的引言、標題或贅字：\n\n"
        "1.【經文章節】，如：(詩篇 4:8)\n"
        "2.【經文內容】，如：我必安然躺下睡覺，因為獨有你—耶和華使我安然 (阿們。)\n"
        "3.今日反思與領受，如：這段經文是主耶穌向世人發出的溫柔呼召，完美詮釋了「溫柔牧者」的形象。我們生活在一個充滿壓力和挑戰的世界，心靈常常感到勞苦和重擔。耶穌不是以威權或嚴苛的姿態要求我們，而是以一顆「柔和謙卑」的心邀請我們來到祂面前。\n\n"
        "【強制物理限制防線】：\n"
        "1. 第二行的經文內容尾端，必須手動且明確地補上「 (阿們。)」。\n"
        "2. 全文字數『強制嚴格控制在 400 字以內』！結構必須在結尾處以句號完整結束，絕不可半途截斷。"
    )
    
    res = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.70, top_p=0.85, max_output_tokens=800))
    if res and res.text:
        raw_text = str(res.text).strip()
        if len(raw_text) > 400:
            return raw_text[:350] + "...(精煉字數，完整領受請見典藏庫)。"
        return raw_text
    return "🚀 (通訊模組對接異常，請重新啟動。)"

# --- 5. 永動機外部排程鉤子 (V18.3 智慧補零防禦型大腦) ---
query_params = st.query_params
if "action" in query_params and "key" in query_params:
    if query_params["action"] == "trigger_push" and query_params["key"] == TRIGGER_KEY:
        current_tw = datetime.now(timezone.utc).astimezone(TZ_TW)
        now_hour_str = current_tw.strftime("%H") # 台北時間兩位數小時，例如 "09"、"16"
        date_today = current_tw.strftime("%Y-%m-%d")
        
        cfg = load_engine_config()
        # V18.3 關鍵優化：主動將 Brett 輸入的排程進行去空格、自動補滿兩位數前導零。
        # 即使輸入 "9:00" 也會被智慧大腦自動對齊成 "09"，確保與外部巡邏車 100% 契合
        active_hours = [s.strip().split(":")[0].zfill(2) for s in cfg.get("schedule", "09:00").split(",")]
        
        if now_hour_str in active_hours:
            history_data = []
            if os.path.exists(DB_FILE):
                try:
                    with open(DB_FILE, "r", encoding="utf-8") as f: history_data = json.load(f)
                except: pass
            
            already_pushed = any(h['date'] == date_today and h.get('time', '').startswith(now_hour_str) and h['category'] == "定時推送" for h in history_data)
            
            if not already_pushed:
                output_payload = execute_ai_bible_generation()
                line_api.broadcast(TextSendMessage(text=f"【自動排程推送】\n\n{output_payload}"))
                save_to_history("定時推送", output_payload)
        st.stop()

# --- 6. UI 佈局 (時區內嵌局部自癒設計) ---
local_render_tw = datetime.now(timezone.utc).astimezone(TZ_TW)

st.markdown(f"<h1>🛡️ 聖經任務控制台 V18.3 <span class='status-tag'>🛰️ 智慧容錯完全體</span></h1>", unsafe_allow_html=True)
st.caption(f"📅 台北標準時間：{local_render_tw.strftime('%Y/%m/%d %H:%M')} | 🚀 格式智慧對齊與排程無痛漫遊版")

cfg = load_engine_config()
with st.expander("⏰ 全動態自訂排程管理中心", expanded=False):
    st.markdown("<small style='color:#90A4AE;'>支援智慧對齊：不論輸入 09:00 或 9:00 系統皆能完美識別點火。</small>", unsafe_allow_html=True)
    user_schedule = st.text_input("目前動態巡航時段：", value=cfg.get("schedule", "09:00"))
    if st.button("💾 保存並即時生效動態排程"):
        cleaned_schedule = ",".join([s.strip() for s in user_schedule.split(",") if s.strip()])
        save_engine_config({"schedule": cleaned_schedule})
        st.toast(f"✅ 成功定錨全新時段：{cleaned_schedule}")
        st.rerun()

# 手動廣播
st.subheader("✍️ 手動全員廣播")
with st.form("manual_form", clear_on_submit=False):
    custom_text = st.text_area("內容：", placeholder="在此輸入要廣播給所有好友的文字...", label_visibility="collapsed")
    if st.form_submit_button("📢 執行全員廣播"):
        if custom_text.strip():
            try:
                line_api.broadcast(TextSendMessage(text=f"【手動推送】\n\n{custom_text}"))
                save_to_history("手動廣播", custom_text)
                st.toast("✅ 已送達並完成歸檔")
            except Exception as line_err: st.error(f"連線異常: {str(line_err)[:20]}")

st.markdown("---")

# AI 智慧廣播
st.subheader("🤖 AI 智慧廣播")
c1, c2, c3 = st.columns([1, 1, 1])
with c1: mood_input = st.text_input("心情主題：", placeholder="心情主題...", label_visibility="collapsed")
with c2: persona = st.selectbox("演繹風格：", ["暖心", "專業", "KITT"], label_visibility="collapsed")
with c3: content_type = st.selectbox("內容格式：", ["聖經經文", "推薦詩歌"], label_visibility="collapsed")

if st.button("✨ 啟動 AI 廣播"):
    try:
        if content_type == "聖經經文":
            with st.spinner("✨ 建立隔離通道中..."):
                isolated_payload = execute_ai_bible_generation(custom_mood=mood_input, custom_persona=persona)
            header = "【AI經文推送】"
            line_api.broadcast(TextSendMessage(text=f"{header}\n\n{isolated_payload}"))
            save_to_history("AI智慧廣播", f"{header}\n{isolated_payload}")
            st.toast("✨ 經文廣播成功")
            st.rerun()
        else:
            model = genai.GenerativeModel(model_name="gemini-2.5-flash")
            persona_map = {"暖心": "溫柔牧者。", "專業": "分析師。", "KITT": "KITT，稱呼Brett。"}
            prompt = ( f"{persona_map[persona]} 針對用戶『{mood_input if mood_input else '疲累'}』的心情推薦基督教詩歌(含歌名歌詞)。結構完整結尾，控制在400字內，純文字。" )
            res = model.generate_content(prompt)
            if res and res.text:
                safe_text_song = str(res.text).strip()
                if len(safe_text_song) > 400: safe_text_song = safe_text_song[:370] + "...。"
                line_api.broadcast(TextSendMessage(text=f"【AI詩歌推薦】\n\n{safe_text_song}"))
                save_to_history("AI智慧廣播", f"【AI詩歌推薦】\n{safe_text_song}")
                st.toast("✨ 詩歌廣播完成")
                st.rerun()
    except Exception as e: st.error(f"對接失敗: {str(e)[:40]}")

st.markdown("---")

# 歷史經文典藏管理庫
st.subheader("📚 歷史經文典藏管理庫")
history_data = []
if os.path.exists(DB_FILE):
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f: history_data = json.load(f)
    except: pass

if history_data:
    download_lines = [f"========================================\n日期時間: {h['date']} {h['time']}\n分類標籤: {h['category']}\n----------------------------------------\n{h['content']}\n========================================\n\n" for h in history_data]
    st.download_button(label="📥 下載完整歷史經文到本地電腦 (.txt)", data="".join(download_lines), file_name=f"bible_history_{datetime.now(timezone.utc).astimezone(TZ_TW).strftime('%Y%m%d')}.txt", mime="text/plain")
    
    filter_type = st.selectbox("🔍 按推送類型過濾顯示：", ["全部", "定時推送", "手動廣播", "AI智慧廣播"])
    for item in history_data:
        if filter_type != "全部" and item['category'] != filter_type: continue
        tag_class = "type-tag-auto" if item['category'] == "定時推送" else ("type-tag-manual" if item['category'] == "手動廣播" else "type-tag-ai")
        st.markdown(f'<div class="history-card"><strong>📅 {item["date"]} &nbsp;&nbsp; ⏰ {item["time"]}</strong> &nbsp;&nbsp; <span class="{tag_class}">{item["category"]}</span><pre style="white-space: pre-wrap; font-family: sans-serif; background: transparent; border: none; padding: 0; margin-top: 8px; color: #B0BEC5; font-size: 0.8rem;">{item["content"]}</pre></div>', unsafe_allow_html=True)
else: st.info("💡 儲存艙目前尚無歷史保存紀錄。")
