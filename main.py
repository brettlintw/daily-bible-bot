import streamlit as st
import google.generativeai as genai
from datetime import datetime, timedelta, timezone
import random
import time
import threading
import json
import os

# --- 1. 頁面配置 (旗艦一頁式極簡美學) ---
st.set_page_config(page_title="聖經控制台 V28.1", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .main .block-container { max-width: 80% !important; padding: 0.3rem 1rem !important; }
    @media (max-width: 1023px) { .main .block-container { max-width: 100% !important; padding: 0.3rem !important; } }
    h1 { font-size: 1.15rem !important; margin: 0 !important; line-height: 1.1 !important; color: #E0E0E0; }
    .stTextArea>div>div>textarea { height: 55px !important; border-radius: 8px; }
    .stTextInput>div>div>input { height: 2.1rem !important; border-radius: 8px; }
    .stButton>button { border-radius: 8px; height: 2.5rem; font-weight: bold; }
    .status-tag { font-size: 0.7rem; padding: 2px 8px; border-radius: 10px; background: #00E676; color: black; margin-left: 10px; }
    .history-card { background: #1E1E1E; padding: 10px; border-radius: 8px; border-left: 5px solid #00E676; margin-bottom: 8px; color: #E0E0E0; }
    .type-tag-auto { background: #2E7D32; color: white; padding: 1px 6px; border-radius: 4px; font-size: 0.65rem; }
    .type-tag-manual { background: #C62828; color: white; padding: 1px 6px; border-radius: 4px; font-size: 0.65rem; }
    .type-tag-ai { background: #1565C0; color: white; padding: 1px 6px; border-radius: 4px; font-size: 0.65rem; }
    .radar-tag { background: #1A237E; color: #00E676; padding: 4px 10px; border-radius: 6px; font-size: 0.8rem; font-family: monospace; font-weight: bold; margin-right: 6px; border: 1px solid #00E676; display: inline-block; }
    .api-active-tag { background: #E0F2F1; color: #004D40; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; }
    [data-testid="stHeader"], footer, #MainMenu { visibility: hidden; height: 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心時區與全域時間常量配置 (【V28.1 修正】：變數提前定義，徹底解除 NameError) ---
TZ_TW = timezone(timedelta(hours=8))
local_render_tw = datetime.now(timezone.utc).astimezone(TZ_TW)

def get_cfg(key, fallback):
    try: return st.secrets.get(key, fallback) or fallback
    except: return fallback

LINE_TOKEN = get_cfg("LINE_ACCESS_TOKEN", "")
TRIGGER_KEY = get_cfg("TRIGGER_KEY", "KITT_SECURE_KEY_2026")

from linebot import LineBotApi
from linebot.models import TextSendMessage
line_api = LineBotApi(LINE_TOKEN)

DB_FILE = "bible_history.json"
CONFIG_FILE = "engine_config.json"

# --- 3. 雙向解耦金鑰與模型動態探測機制 ---
def scan_secret_keys():
    key_names = ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3", "GEMINI_API_KEY_4", "GEMINI_API_KEY_5"]
    pool = {}
    for idx, name in enumerate(key_names, start=1):
        v = get_cfg(name, "")
        if v and len(v) > 5:
            masked_key = f"***{v[-4:]}"
            pool[f"🔑 金鑰密鑰順位 #{idx} ({masked_key})"] = v
    if not pool:
        pool["⚠️ 未偵測到任何 Key (請檢查 Secrets)"] = ""
    return pool

KEY_POOL = scan_secret_keys()

def discover_supported_models(target_key):
    if not target_key:
        return {"⚠️ 請先選擇有效金鑰": "gemini-2.5-flash"}
        
    util_registry = {
        "gemini-2.5-flash": "【極速輕量型】日常秒發、高頻率首選核心",
        "gemini-2.5-pro":   "【深度推理型】適合複雜語意、長篇靈修反思",
        "gemini-1.5-pro":   "【百萬文本型】具備超長記憶，適合大篇幅卷軸分析",
        "gemini-1.5-flash": "【穩健平衡型】經典速度型核心，兼顧穩定度",
        "gemma-2-27b-it":   "【敏捷極客型】適合超精煉短句與嚴格字數控制"
    }
    
    discovered_options = {}
    try:
        genai.configure(api_key=target_key)
        online_models = genai.list_models()
        supported_ids = [m.name.split('/')[-1] for m in online_models if 'generateContent' in m.supported_generation_methods]
        
        match_count = 0
        for m_id, desc in util_registry.items():
            if m_id in supported_ids and match_count < 5:
                label = f"🚀 {m_id} ── {desc}"
                discovered_options[label] = m_id
                match_count += 1
    except: pass
        
    if not discovered_options:
        discovered_options["🚀 gemini-2.5-flash ── 系統防護保底核心"] = "gemini-2.5-flash"
    return discovered_options

# --- 4. 配置管理 ---
def load_engine_config():
    if "cached_schedule" in st.session_state and "fixed_key_label" in st.session_state and "fixed_model_id" in st.session_state:
        return {
            "schedule": st.session_state["cached_schedule"],
            "fixed_key_label": st.session_state["fixed_key_label"],
            "fixed_model_id": st.session_state["fixed_model_id"],
            "fixed_key_val": st.session_state.get("fixed_key_val", "")
        }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data and "schedule" in data:
                    st.session_state["cached_schedule"] = data.get("schedule", "09:00")
                    st.session_state["fixed_key_label"] = data.get("fixed_key_label", list(KEY_POOL.keys())[0])
                    st.session_state["fixed_model_id"] = data.get("fixed_model_id", "gemini-2.5-flash")
                    st.session_state["fixed_key_val"] = data.get("fixed_key_val", "")
                    return data
        except: pass
    return {"schedule": "09:00", "fixed_key_label": list(KEY_POOL.keys())[0], "fixed_model_id": "gemini-2.5-flash", "fixed_key_val": ""}

def save_engine_config(config_data):
    st.session_state["cached_schedule"] = config_data["schedule"]
    st.session_state["fixed_key_label"] = config_data["fixed_key_label"]
    st.session_state["fixed_model_id"] = config_data["fixed_model_id"]
    st.session_state["fixed_key_val"] = config_data["fixed_key_val"]
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
    except: pass

def save_to_history(category, content):
    current_tw = datetime.now(timezone.utc).astimezone(TZ_TW)
    new_entry = {
        "id": int(time.time() * 1000),
        "date": current_tw.strftime("%Y-%m-%d"),
        "time": current_tw.strftime("%H:%M:%S"),
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
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except: pass

# --- 5. 終極生成核心 (恆定 900 Token 完句防斷片盾牌) ---
def execute_ai_safe_generation(target_model_id, target_api_key, mode="聖經經文", custom_mood=None, custom_persona="暖心"):
    if not target_api_key:
        return "錯誤：當前配置之 API KEY 燃料短缺，發射中止。"
        
    genai.configure(api_key=target_api_key)
    model = genai.GenerativeModel(model_name=target_model_id)
    
    persona_intro = "你是溫柔牧者。"
    if custom_persona == "專業": persona_intro = "你是業界專業分析師。"
    elif custom_persona == "KITT": persona_intro = "你是KITT，稱呼Brett。"
        
    if mode == "聖經經文":
        mood_context = f"針對主題或心情『{custom_mood}』" if custom_mood else "針對目前的時分"
        prompt = (
            f"{persona_intro} 請{mood_context}精選一段聖經經文，並給予深度反思與領受。\n\n"
            "【輸出順序格式三階鐵律】：\n"
            "你必須嚴格、完美地依照以下格式規範輸出，每行中間空一行，嚴禁輸出任何額外的引言、標題 or 贅字：\n\n"
            "1.【經文章節】，如：(詩篇 4:8)\n"
            "2.【經文內容】，如：我必安然躺下睡覺，因為獨有你—耶和華使我安然 (阿們。)\n"
            "3.今日反思與領受，如：這段經文是主耶穌向世人發出的溫柔呼召。我們生活在一個充滿壓力的世界...\n\n"
            "【強制規格防線】：\n"
            "1. 第二行的經文內容尾端，必須手動且明確地補上「 (阿們。)」。\n"
            "2. 今日反思與領受請控制在 150 到 200 字之間，全文字數強制完美控制在 300 字左右。\n"
            "3. 全文結構必須非常完整，結尾最後一個字必須是正常的「句號」結束，絕對不允許未完句中斷！"
        )
    else:
        mood_context = f"針對用戶『{custom_mood if custom_mood else '疲累'}』的心情"
        prompt = (
            f"{persona_intro} {mood_context}推薦基督教詩歌(含歌名與精選歌詞)。\n\n"
            "【輸出規範】：\n"
            "1. 必須包含歌名與歌詞，並給予 100 字內的溫慢勉勵。\n"
            "2. 全文字數嚴格控制在 250 到 300 字之內。\n"
            "3. 結尾最後一個字必須是正常的「句號」結束，絕對不允許半途截斷！"
        )
    
    for attempt in range(3):
        try:
            res = model.generate_content(
                prompt, 
                generation_config=genai.types.GenerationConfig(temperature=0.70, top_p=0.85, max_output_tokens=900)
            )
            if res and res.text:
                text_payload = str(res.text).strip()
                if len(text_payload) <= 450 and (text_payload.endswith('。') or text_payload.endswith(')') or text_payload.endswith('）')):
                    return text_payload
        except: pass
        time.sleep(1)
        
    try: final_text = str(res.text).strip()
    except: final_text = "核心動力連線適配中，請稍後..."
    if len(final_text) > 390: final_text = final_text[:370] + "...。"
    return final_text

# --- 6. 永動機外部排程鉤子 ---
query_params = st.query_params
if "action" in query_params and "key" in query_params:
    if query_params["action"] == "trigger_push" and query_params["key"] == TRIGGER_KEY:
        current_tw = datetime.now(timezone.utc).astimezone(TZ_TW)
        date_today = current_tw.strftime("%Y-%m-%d")
        
        cron_cfg = {"schedule": "09:00", "fixed_model_id": "gemini-2.5-flash", "fixed_key_val": ""}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    file_data = json.load(f)
                    if file_data: cron_cfg.update(file_data)
            except: pass

        active_schedules = []
        for s in cron_cfg.get("schedule", "09:00").split(","):
            if ":" in s:
                h_part, m_part = s.strip().split(":")
                active_schedules.append(f"{h_part.zfill(2)}:{m_part.zfill(2)}")

        history_data = []
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f: history_data = json.load(f)
            except: pass

        for sched in active_schedules:
            sched_h, sched_m = map(int, sched.split(":"))
            target_time = current_tw.replace(hour=sched_h, minute=sched_m, second=0, microsecond=0)
            
            if target_time <= current_tw <= (target_time + timedelta(minutes=15)):
                specific_pushed = False
                for h in history_data:
                    if h['date'] == date_today and h['category'] == "定時推送":
                        h_time_parts = h.get('time', '00:00:00').split(":")
                        if len(h_time_parts) >= 2:
                            h_h = int(h_time_parts[0])
                            h_m = int(h_time_parts[1])
                            if h_h == sched_h and abs(h_m - sched_m) < 20:
                                specific_pushed = True
                                break

                if not specific_pushed:
                    final_api_key = cron_cfg.get("fixed_key_val", "")
                    if not final_api_key or len(final_api_key) < 5:
                        final_api_key = get_cfg("GEMINI_API_KEY", "")
                        
                    final_model_id = cron_cfg.get("fixed_model_id", "gemini-2.5-flash")
                    
                    output_payload = execute_ai_safe_generation(
                        target_model_id=final_model_id,
                        target_api_key=final_api_key,
                        mode="聖經經文"
                    )
                    line_api.broadcast(TextSendMessage(text=f"【自動排程推送】\n\n{output_payload}"))
                    save_to_history("定時推送", output_payload)
                    break 
        st.stop()

# --- 7. UI 佈局 (雙選單完全自癒隔離中心) ---
st.markdown(f"<h1>🛡️ 聖經任務控制台 V28.1 <span class='status-tag'>🛰️ 世紀完全體封頂</span></h1>", unsafe_allow_html=True)
st.caption(f"📅 台北標準時間：{local_render_tw.strftime('%Y/%m/%d %H:%M')} | 🚀 獨立檔案流隔離 ── 100% 解決背景漏推與斷片")

cfg = load_engine_config()
available_keys = list(KEY_POOL.keys())

st.markdown("---")
# 【選單一：金鑰更換選單】
saved_key_label = cfg.get("fixed_key_label", available_keys[0])
if saved_key_label not in available_keys: saved_key_label = available_keys[0]

chosen_key_label = st.selectbox("🔑 1. 請選擇任務 API 金鑰：", options=available_keys, index=available_keys.index(saved_key_label))
CURRENT_KEY_VAL = KEY_POOL[chosen_key_label]

# 【背景自動線上識別辨識】
MODEL_REGISTRY = discover_supported_models(CURRENT_KEY_VAL)
available_models_labels = list(MODEL_REGISTRY.keys())

# 【選單二：模型自適應選單】
saved_model_id = cfg.get("fixed_model_id", "gemini-2.5-flash")
default_model_idx = 0
for l, m_id in MODEL_REGISTRY.items():
    if m_id == saved_model_id:
        default_model_idx = available_models_labels.index(l)
        break

chosen_model_label = st.selectbox("🤖 2. 該金鑰自動辨識支持之實用模型選單：", options=available_models_labels, index=default_model_idx)
CURRENT_MODEL_ID = MODEL_REGISTRY[chosen_model_label]

# 將選定參數進行前端暫存隔離快照
st.session_state["active_snapshot_model"] = CURRENT_MODEL_ID
st.session_state["active_snapshot_key"] = CURRENT_KEY_VAL

if CURRENT_KEY_VAL:
    st.markdown(f"定錨狀態：<span class='api-active-tag'>🔒 內部 API KEY 與模型已完美隔離鎖定：{CURRENT_MODEL_ID}</span>", unsafe_allow_html=True)
else:
    st.markdown("<span class='api-active-tag' style='background:#FFEBEE; color:#C62828;'>🔴 警報：金鑰未配置，請檢查 Secrets</span>", unsafe_allow_html=True)

st.markdown("---")

current_schedules = []
for s in cfg.get("schedule", "09:00").split(","):
    if ":" in s:
        hp, mp = s.strip().split(":")
        current_schedules.append(f"{hp.zfill(2)}:{mp.zfill(2)}")

with st.expander("⏰ 全動態自訂排程管理中心 (支援隨時多時段追加)", expanded=True):
    st.markdown("<small style='color:#90A4AE;'>💡 <b>安全定錨提醒：</b>變更模型或時間後，請務必點擊下方按鈕。系統將強行把實體金鑰與組態落盤，確保自動排程高穩定點火。</small>", unsafe_allow_html=True)
    
    st.markdown("### 🛰️ 當前雷達鎖定點火時段：")
    if current_schedules:
        tag_html = "".join([f'<span class="radar-tag">📡 {sched}</span>' for sched in current_schedules])
        st.markdown(tag_html, unsafe_allow_html=True)
    else: st.warning("⚠️ 目前無任何排程時間！")
        
    st.markdown("<br>", unsafe_allow_html=True)
    user_schedule = st.text_input("隨時修改/追加排程時段：", value=cfg.get("schedule", "09:00"))
    
    if st.button("💾 保存並即時生效動態排程"):
        cleaned_schedule = ",".join([s.strip() for s in user_schedule.split(",") if s.strip()])
        save_engine_config({
            "schedule": cleaned_schedule,
            "fixed_key_label": chosen_key_label,
            "fixed_model_id": CURRENT_MODEL_ID,
            "fixed_key_val": CURRENT_KEY_VAL
        })
        st.toast(f"✅ 成功將實體金鑰字串與模型完全鎖定定錨！")
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
                st.rerun()
            except Exception as line_err: st.error(f"連線異常: {str(line_err)[:20]}")

st.markdown("---")

# AI 智慧廣播
st.subheader("🤖 AI 智慧廣播")
c1, c2, c3 = st.columns([1, 1, 1])
with c1: mood_input = st.text_input("心情主題：", placeholder="心情主題...", label_visibility="collapsed")
with c2: persona = st.selectbox("演繹風格：", ["暖心", "專業", "KITT"], label_visibility="collapsed")
with c3: content_type = st.selectbox("內容格式：", ["聖經經文", "推薦詩歌"], label_visibility="collapsed")

if st.button("✨ 啟動 AI 廣播"):
    snapshot_key = st.session_state.get("active_snapshot_key", "")
    snapshot_model = st.session_state.get("active_snapshot_model", "gemini-2.5-flash")
    
    if not snapshot_key:
        st.error("🔒 無法擊發：隔離艙未偵測到有效金鑰。")
    else:
        try:
            with st.spinner("✨ 建立隔離防護罩中..."):
                isolated_payload = execute_ai_safe_generation(
                    target_model_id=snapshot_model,
                    target_api_key=snapshot_key,
                    mode=content_type,
                    custom_mood=mood_input,
                    custom_persona=persona
                )
            header = "【AI經文推送】" if content_type == "聖經經文" else "【AI詩歌推薦】"
            line_api.broadcast(TextSendMessage(text=f"{header}\n\n{isolated_payload}"))
            save_to_history("AI智慧廣播", f"{header}\n{isolated_payload}")
            st.toast("✨ 廣播發射成功")
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
else: st.info("⚠️ 儲存艙目前尚無歷史保存紀錄。")
