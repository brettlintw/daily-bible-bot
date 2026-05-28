import streamlit as st
import google.generativeai as genai
from datetime import datetime, timedelta, timezone
import random
import time
import threading
import json
import os

# --- 這裡就是黃金位置 ---
os.environ['TZ'] = 'Asia/Taipei'

# --- 0. 系統版本宣告 (主程式與後台核心定錨) ---
SYSTEM_VERSION = "V42.7"

# --- 1. 頁面配置 (旗艦一頁式極簡美學 ── 強裝標題絕對不折行盔甲) ---
st.set_page_config(page_title=f"聖經控制台 {SYSTEM_VERSION}", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .main .block-container { max-width: 80% !important; padding: 0.3rem 1rem !important; }
    @media (max-width: 1023px) { 
        .main .block-container { max-width: 100% !important; padding: 0.2rem 0.5rem !important; } 
        h1 { font-size: 0.95rem !important; white-space: nowrap !important; display: flex !important; align-items: center !important; flex-wrap: nowrap !important; }
        .status-tag { font-size: 0.6rem !important; padding: 1px 4px !important; margin-left: 4px !important; white-space: nowrap !important; }
        .schedule-radar-box { padding: 8px !important; }
        .schedule-radar-box code { font-size: 0.95rem !important; }
        .api-active-tag { display: inline-block; margin-top: 4px; padding: 4px 6px !important; font-size: 0.7rem !important; line-height: 1.2 !important; }
    }
    h1 { font-size: 1.15rem !important; margin: 0 !important; line-height: 1.1 !important; color: #E0E0E0; white-space: nowrap !important; }
    .stTextArea>div>div>textarea { height: 55px !important; border-radius: 8px; }
    .stTextInput>div>div>input { height: 2.1rem !important; border-radius: 8px; }
    .stButton>button { border-radius: 8px; height: 2.5rem; font-weight: bold; }
    .status-tag { font-size: 0.7rem; padding: 2px 8px; border-radius: 10px; background: #00E676; color: black; margin-left: 10px; white-space: nowrap !important; border: none !important; display: inline-block !important; }
    .history-card { background: #1E1E1E; padding: 10px; border-radius: 8px; border-left: 5px solid #00E676; margin-bottom: 8px; color: #E0E0E0; }
    .type-tag-auto { background: #2E7D32; color: white; padding: 1px 6px; border-radius: 4px; font-size: 0.65rem; }
    .type-tag-manual { background: #C62828; color: white; padding: 1px 6px; border-radius: 4px; font-size: 0.65rem; }
    .type-tag-multicast { background: #E65100; color: white; padding: 1px 6px; border-radius: 4px; font-size: 0.65rem; }
    .type-tag-ai { background: #1565C0; color: white; padding: 1px 6px; border-radius: 4px; font-size: 0.65rem; }
    .radar-tag { background: #1A237E; color: #00E676; padding: 4px 10px; border-radius: 6px; font-size: 0.8rem; font-family: monospace; font-weight: bold; margin-right: 6px; border: 1px solid #00E676; display: inline-block; }
    .api-active-tag { background: #E0F2F1; color: #004D40; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; white-space: normal !important; word-break: break-all !important; }
    .billing-free { color: #FF9100; font-weight: bold; font-family: monospace; }
    .billing-paid { color: #00E676; font-weight: bold; font-family: monospace; }
    .self-radar-box { background: #3E2723; border: 1px dashed #FF9100; border-radius: 8px; padding: 10px; margin-bottom: 15px; color: #FFD180; font-family: monospace; font-size: 0.85rem; }
    .schedule-radar-box { background: #1A237E; border: 1px solid #00E676; border-radius: 8px; padding: 10px; margin-bottom: 15px; color: #00E676; font-family: monospace; font-size: 0.85rem; width: 100%; box-sizing: border-box; }
    [data-testid="stHeader"], footer, #MainMenu { visibility: hidden; height: 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心時區與全域時間配置 ---
# 確保在任何時間函式呼叫前設定環境變數
TZ_TW = timezone(timedelta(hours=8))
def get_cfg(key, fallback):
    try: 
        return st.secrets.get(key, fallback) or fallback
    except: 
        return fallback

LINE_TOKEN = get_cfg("LINE_ACCESS_TOKEN", "")
TRIGGER_KEY = get_cfg("TRIGGER_KEY", "KITT_SECURE_KEY_2026")

from linebot import LineBotApi
from linebot.models import TextSendMessage

# 確保 line_api 在全域範圍內初始化
line_api = LineBotApi(LINE_TOKEN)

DB_FILE = "bible_history.json"
CONFIG_FILE = "engine_config.json"
RADAR_TRACK_FILE = "radar_user_track.json"

# --- 3. 金鑰與模型動態探測中樞 ---
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
        return {"⚠️ 請先選擇有效金鑰": {"model_id": "gemini-2.5-flash", "billing": "免費版"}}
        
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
        
        model_quota_map = {}
        for m in online_models:
            m_short_id = m.name.split('/')[-1]
            is_free_tier = True
            if "generateContent" in m.supported_generation_methods:
                if hasattr(m, "text_to_image_count_limit") or m.name.endswith("-search") or "lite" in m.name:
                    is_free_tier = True
                else:
                    is_free_tier = False
                model_quota_map[m_short_id] = "免費版" if is_free_tier else "付費版"
        
        match_count = 0
        for m_id, desc in util_registry.items():
            if any(m_id in m.name for m in genai.list_models()) and match_count < 5:
                tier_status = model_quota_map.get(m_id, "付費版")
                label = f"🚀 {m_id} ── [{tier_status}] {desc}"
                discovered_options[label] = {
                    "model_id": m_id,
                    "billing": tier_status
                }
                match_count += 1
    except: pass
        
    if not discovered_options:
        discovered_options["🚀 gemini-2.5-flash ── [免費版] 系統防護保底核心"] = {"model_id": "gemini-2.5-flash", "billing": "免費版"}
    return discovered_options

# --- 4. 配置管理 ---
def load_engine_config():
    default_config = {
        "daily_enabled": True,
        "daily_t1_enabled": True,
        "daily_t2_enabled": True,
        "daily_t3_enabled": True,
        "daily_schedule": "09:00,15:30,21:00",
        
        "specific_enabled": True,
        "specific_t1_enabled": True,
        "specific_t2_enabled": True,
        "specific_t3_enabled": True,
        "specific_schedule": "09:00,15:30,21:00",
        "specific_date": datetime.now(TZ_TW).strftime("%Y-%m-%d"),
        
        "fixed_key_label": list(KEY_POOL.keys())[0] if KEY_POOL else "",
        "fixed_model_id": "gemini-2.5-flash",
        "fixed_key_val": ""
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data:
                    if "schedule" in data and "daily_schedule" not in data:
                        data["daily_schedule"] = data["schedule"]
                    for k, v in default_config.items():
                        if k not in data: data[k] = v
                    return data
        except: pass
    return default_config

def save_engine_config(config_data):
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

# --- 5. 終極生成核心 (token 4096防線) ---
def execute_ai_safe_generation(target_model_id, target_api_key, mode="聖經經文", custom_mood=None, custom_persona="暖心"):
    if not target_api_key: return "燃料短缺，發射中止。"
    
    genai.configure(api_key=target_api_key)
    model = genai.GenerativeModel(model_name=target_model_id)
    
    # 調整 Prompt：加入「嚴格不要中斷」的指示
    prompt = f"你是溫柔牧者。請精選一段聖經經文，並給予深度反思。請確保內容完整，絕對不要在句子中間截斷。如果內容過長，請精簡，但必須要有一個完整的收尾。\n\n【輸出順序】\n【經文內容】\n【經文章節】\n【領受與感悟】\n\n以句號結尾。"
    
    for attempt in range(3):
        try:
            # 提升 Token 額度到 4096
            res = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.7, max_output_tokens=4096))
            if res and res.text:
                text = str(res.text).strip()
                # 容錯邏輯：如果沒有句號，強行補上，確保閱讀體驗
                if not (text.endswith('。') or text.endswith('！') or text.endswith(')')):
                    text += "。"
                return text
        except: pass
        time.sleep(2) # 增加重試間隔
    return "系統稍後恢復，請稍後。"
# --- 6. 永動機外部排程與 Webhook 雙軌中樞 (V41.3.4 全時自癒硬化模組) ---
query_params = st.query_params

    
if "incoming_uid" in query_params:
    try:
        radar_data = {
            "last_seen_uid": query_params["incoming_uid"],
            "timestamp": datetime.now(timezone.utc).astimezone(TZ_TW).strftime("%H:%M:%S")
        }
        with open(RADAR_TRACK_FILE, "w", encoding="utf-8") as f:
            json.dump(radar_data, f, ensure_ascii=False, indent=4)
    except: pass
    st.write("OK")
    st.stop()

if "action" in query_params and "key" in query_params:
    if query_params["action"] == "trigger_push" and query_params["key"] == TRIGGER_KEY:
        # 🛡️ 鋼鐵自癒防線 1：強制執行最高優先級之 UTC 轉台灣時區定錨
        current_tw = datetime.now(timezone.utc).astimezone(TZ_TW)
        date_today = current_tw.strftime("%Y-%m-%d")
        
        cron_cfg = load_engine_config()
        target_schedules = []
        
        # 軌道 A：每日固定循環
        if cron_cfg.get("daily_enabled", True):
            d_times = cron_cfg.get("daily_schedule", "09:00,15:30,21:00").split(",")
            d_gates = [cron_cfg.get("daily_t1_enabled", True), cron_cfg.get("daily_t2_enabled", True), cron_cfg.get("daily_t3_enabled", True)]
            for idx, s in enumerate(d_times):
                if idx < len(d_gates) and d_gates[idx] and ":" in s.strip():
                    h, m = s.strip().split(":")
                    target_schedules.append({"hour": h.zfill(2), "minute": m.zfill(2)})
                
        # 軌道 B：特定單日狙擊
        if cron_cfg.get("specific_enabled", True) and cron_cfg.get("specific_date", "") == date_today:
            s_times = cron_cfg.get("specific_schedule", "09:00,15:30,21:00").split(",")
            s_gates = [cron_cfg.get("specific_t1_enabled", True), cron_cfg.get("specific_t2_enabled", True), cron_cfg.get("specific_t3_enabled", True)]
            for idx, s in enumerate(s_times):
                if idx < len(s_gates) and s_gates[idx] and ":" in s.strip():
                    h, m = s.strip().split(":")
                    target_schedules.append({"hour": h.zfill(2), "minute": m.zfill(2)})

        history_data = []
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f: history_data = json.load(f)
            except: pass

        for task in target_schedules:
            sched_h, sched_m = map(int, [task["hour"], task["minute"]])
            target_time = current_tw.replace(hour=sched_h, minute=sched_m, second=0, microsecond=0)
            
# --- 絕對穩定版 (請確保貼上時完全無前導空白) ---
# --- 終極修正後結構 ---
if is_time_ok:
    already_sent = any(h['date'] == date_today and h['category'] == "排程推送" for h in history_data)
    if not already_sent:
        try:
            output = execute_ai_safe_generation(target_model_id="gemini-2.5-flash", target_api_key=get_cfg("GEMINI_API_KEY", ""), mode="聖經經文")
            line_api.broadcast(TextSendMessage(text=f"【自動排程推送】\n\n{output}"))
            save_to_history("排程推送", output)
            st.success("✅ 發送成功")
        except Exception as e:
            st.error(f"🚨 LINE發射失敗: {str(e)}")

# --- 這裡直接接結束動作 ---
st.write("CRON_PROCESSED")
st.stop()

# --- 7. UI 佈局 ---
st.markdown(f"<h1>🛡️ 聖經任務控制台 {SYSTEM_VERSION} <span class='status-tag'>🛰️ 聯邦制導</span><span class='status-tag' style='background:#00E676; color:black;'>全時自動巡航體</span></h1>", unsafe_allow_html=True)
st.caption(f"📅 台北標準時間：{local_render_tw.strftime('%Y/%m/%d %H:%M')} | 🚀 25分鐘補發自癒加固版 [當前版本: {SYSTEM_VERSION}]")

cfg = load_engine_config()
daily_enabled = cfg.get("daily_enabled", True)
daily_show = cfg.get("daily_schedule", "09:00,15:30,21:00")
specific_enabled = cfg.get("specific_enabled", True)
specific_date_show = cfg.get("specific_date", "")
specific_time_show = cfg.get("specific_schedule", "09:00,15:30,21:00")

daily_active_list = []
d_times = daily_show.split(",")
if daily_enabled:
    if cfg.get("daily_t1_enabled", True) and len(d_times) > 0: daily_active_list.append(d_times[0].strip())
    if cfg.get("daily_t2_enabled", True) and len(d_times) > 1: daily_active_list.append(d_times[1].strip())
    if cfg.get("daily_t3_enabled", True) and len(d_times) > 2: daily_active_list.append(d_times[2].strip())
daily_final_show = ",".join(daily_active_list) if daily_active_list else "🚫 已無啟用時段"

spec_active_list = []
s_times = specific_time_show.split(",")
if specific_enabled:
    if cfg.get("specific_t1_enabled", True) and len(s_times) > 0: spec_active_list.append(s_times[0].strip())
    if cfg.get("specific_t2_enabled", True) and len(s_times) > 1: spec_active_list.append(s_times[1].strip())
    if cfg.get("specific_t3_enabled", True) and len(s_times) > 2: spec_active_list.append(s_times[2].strip())
spec_final_show = f"📅 {specific_date_show} ── ⏰ " + ",".join(spec_active_list) if spec_active_list else "🚫 已無啟用時段"

st.markdown(f"""
<div class="schedule-radar-box">
    ⏰ <b>[自動巡航雙模共存確認牆]</b> 目前核心平行鎖定有效排程：<br>
    <span style='color:#00E676; font-weight:bold;'>🔄 每日循環：</span><code>{daily_final_show}</code><br>
    <span style='color:#FF9100; font-weight:bold;'>🎯 單日狙擊：</span><code>{spec_final_show}</code>
</div>
""", unsafe_allow_html=True)

if os.path.exists(RADAR_TRACK_FILE):
    try:
        with open(RADAR_TRACK_FILE, "r", encoding="utf-8") as f:
            track = json.load(f)
            if track and "last_seen_uid" in track:
                st.markdown(f"""
                <div class="self-radar-box">
                    📡 <b>[雷達即時偵測]</b> 用戶根座標：<code>{track['last_seen_uid']}</code>
                </div>
                """, unsafe_allow_html=True)
    except: pass

available_keys = list(KEY_POOL.keys())

st.markdown("---")
default_key_idx = 0
if cfg.get("fixed_key_label") in available_keys:
    default_key_idx = available_keys.index(cfg["fixed_key_label"])
chosen_key_label = st.selectbox("🔑 1. 請選擇任務 API 金鑰：", options=available_keys, index=default_key_idx)
CURRENT_KEY_VAL = KEY_POOL[chosen_key_label]

MODEL_REGISTRY = discover_supported_models(CURRENT_KEY_VAL)
available_models_labels = list(MODEL_REGISTRY.keys())

saved_model_id = cfg.get("fixed_model_id", "gemini-2.5-flash")
default_model_idx = 0
for l, data in MODEL_REGISTRY.items():
    if data["model_id"] == saved_model_id:
        default_model_idx = available_models_labels.index(l)
        break

chosen_model_label = st.selectbox("🤖 2. 該金鑰自動辨識支持之費用模型選單：", options=available_models_labels, index=default_model_idx)
CURRENT_MODEL_ID = MODEL_REGISTRY[chosen_model_label]["model_id"]
CURRENT_BILLING_STATUS = MODEL_REGISTRY[chosen_model_label]["billing"]

st.session_state["active_snapshot_model"] = CURRENT_MODEL_ID
st.session_state["active_snapshot_key"] = CURRENT_KEY_VAL

if CURRENT_KEY_VAL:
    color_class = "billing-paid" if CURRENT_BILLING_STATUS == "付費版" else "billing-free"
    st.markdown(f"<div style='margin-top:5px; line-height:1.4;'>定錨狀態：<span class='api-active-tag'>🔒 內部 API 完美鎖定：{CURRENT_MODEL_ID} (<b class='{color_class}'>{CURRENT_BILLING_STATUS}</b>)</span></div>", unsafe_allow_html=True)

st.markdown("---")

# --- ⏰ 3. 自動巡航排程設定面板 ---
st.markdown("### ⏰ 3. 自動巡航排程設定面板")

# 舊配置還原
d_parts = cfg.get("daily_schedule", "09:00,15:30,21:00").split(",")
d_t1 = datetime.now(TZ_TW).replace(hour=int(d_parts[0].split(":")[0]), minute=int(d_parts[0].split(":")[1])).time()
d_t2 = datetime.now(TZ_TW).replace(hour=int(d_parts[1].split(":")[0]), minute=int(d_parts[1].split(":")[1])).time() if len(d_parts) > 1 else datetime.now(TZ_TW).replace(hour=15, minute=30).time()
d_t3 = datetime.now(TZ_TW).replace(hour=int(d_parts[2].split(":")[0]), minute=int(d_parts[2].split(":")[1])).time() if len(d_parts) > 2 else datetime.now(TZ_TW).replace(hour=21, minute=0).time()

s_parts = cfg.get("specific_schedule", "09:00,15:30,21:00").split(",")
s_t1 = datetime.now(TZ_TW).replace(hour=int(s_parts[0].split(":")[0]), minute=int(s_parts[0].split(":")[1])).time()
s_t2 = datetime.now(TZ_TW).replace(hour=int(s_parts[1].split(":")[0]), minute=int(s_parts[1].split(":")[1])).time() if len(s_parts) > 1 else datetime.now(TZ_TW).replace(hour=15, minute=30).time()
s_t3 = datetime.now(TZ_TW).replace(hour=int(s_parts[2].split(":")[0]), minute=int(s_parts[2].split(":")[1])).time() if len(s_parts) > 2 else datetime.now(TZ_TW).replace(hour=21, minute=0).time()
try: saved_date_obj = datetime.strptime(cfg.get("specific_date", ""), "%Y-%m-%d").date()
except: saved_date_obj = datetime.now(TZ_TW).date()

tab_daily, tab_specific = st.tabs(["🔄 每一天固定循環推送設定", "🎯 僅在特定年月日發送設定"])

with tab_daily:
    st.markdown("<div style='padding:5px;'></div>", unsafe_allow_html=True)
    ui_daily_enabled = st.toggle("🟩 啟用此模式總開關 (每日固定循環)", value=cfg.get("daily_enabled", True), key="ui_daily_toggle")
    st.markdown("---")
    
    c_d1, c_d2 = st.columns([1, 2])
    with c_d1: ui_d_t1_en = st.toggle("🔌 第一段點火狀態", value=cfg.get("daily_t1_enabled", True), key="ui_dt1_en", disabled=not ui_daily_enabled)
    with c_d2: daily_t1 = st.time_input("選擇時間 (每日1)：", value=d_t1, key="ui_d_t1", disabled=not (ui_daily_enabled and ui_d_t1_en), label_visibility="collapsed")
    
    c_d3, c_d4 = st.columns([1, 2])
    with c_d3: ui_d_t2_en = st.toggle("🔌 第二段點火狀態", value=cfg.get("daily_t2_enabled", True), key="ui_dt2_en", disabled=not ui_daily_enabled)
    with c_d4: daily_t2 = st.time_input("選擇時間 (每日2)：", value=d_t2, key="ui_d_t2", disabled=not (ui_daily_enabled and ui_d_t2_en), label_visibility="collapsed")
    
    c_d5, c_d6 = st.columns([1, 2])
    with c_d5: ui_d_t3_en = st.toggle("🔌 第三段點火狀態", value=cfg.get("daily_t3_enabled", True), key="ui_dt3_en", disabled=not ui_daily_enabled)
    with c_d6: daily_t3 = st.time_input("選擇時間 (每日3)：", value=d_t3, key="ui_d_t3", disabled=not (ui_daily_enabled and ui_d_t3_en), label_visibility="collapsed")

with tab_specific:
    st.markdown("<div style='padding:5px;'></div>", unsafe_allow_html=True)
    ui_specific_enabled = st.toggle("🟨 啟用此模式總開關 (特定單日狙擊)", value=cfg.get("specific_enabled", True), key="ui_spec_toggle")
    target_date_obj = st.date_input("📅 選擇精準狙擊日期：", value=saved_date_obj, key="ui_s_date", disabled=not ui_specific_enabled)
    st.markdown("---")
    
    c_s1, c_s2 = st.columns([1, 2])
    with c_s1: ui_s_t1_en = st.toggle("🔌 狙擊點火 1 狀態", value=cfg.get("specific_t1_enabled", True), key="ui_st1_en", disabled=not ui_specific_enabled)
    with c_s2: spec_t1 = st.time_input("選擇時間 (狙擊1)：", value=s_t1, key="ui_s_t1", disabled=not (ui_specific_enabled and ui_s_t1_en), label_visibility="collapsed")
    
    c_s3, c_s4 = st.columns([1, 2])
    with c_s3: ui_s_t2_en = st.toggle("🔌 狙擊點火 2 狀態", value=cfg.get("specific_t2_enabled", True), key="ui_st2_en", disabled=not ui_specific_enabled)
    with c_s4: spec_t2 = st.time_input("選擇時間 (狙擊2)：", value=s_t2, key="ui_s_t2", disabled=not (ui_specific_enabled and ui_s_t2_en), label_visibility="collapsed")
    
    c_s5, c_s6 = st.columns([1, 2])
    with c_s5: ui_s_t3_en = st.toggle("🔌 狙擊點火 3 狀態", value=cfg.get("specific_t3_enabled", True), key="ui_st3_en", disabled=not ui_specific_enabled)
    with c_s6: spec_t3 = st.time_input("選擇時間 (狙擊3)：", value=s_t3, key="ui_s_t3", disabled=not (ui_specific_enabled and ui_s_t3_en), label_visibility="collapsed")

st.markdown("<div style='margin-top:5px;'></div>", unsafe_allow_html=True)

if st.button("💾 保存雙模式平行共存排程設定", key="SAVE_V41_3_4"):
    final_daily_str = f"{daily_t1.strftime('%H:%M')},{daily_t2.strftime('%H:%M')},{daily_t3.strftime('%H:%M')}"
    final_spec_str = f"{spec_t1.strftime('%H:%M')},{spec_t2.strftime('%H:%M')},{spec_t3.strftime('%H:%M')}"
    
    save_engine_config({
        "daily_enabled": ui_daily_enabled,
        "daily_t1_enabled": ui_d_t1_en,
        "daily_t2_enabled": ui_d_t2_en,
        "daily_t3_enabled": ui_d_t3_en,
        "daily_schedule": final_daily_str,
        
        "specific_enabled": ui_specific_enabled,
        "specific_t1_enabled": ui_s_t1_en,
        "specific_t2_enabled": ui_s_t2_en,
        "specific_t3_enabled": ui_s_t3_en,
        "specific_schedule": final_spec_str,
        "specific_date": target_date_obj.strftime("%Y-%m-%d"),
        
        "fixed_key_label": chosen_key_label,
        "fixed_model_id": CURRENT_MODEL_ID,
        "fixed_key_val": CURRENT_KEY_VAL
    })
    st.toast(f"<b>[巡航自癒加固成功]</b> 配置已鎖定落盤！")
    st.rerun()

# --- 手動精準推送中樞 ---
st.markdown("---")
st.subheader("✍️ 手動精準推送中樞")

target_mode = st.radio(
    "🎯 請選擇發射精準維度：", 
    ["全員廣播 (Broadcast)", "單人/多人精準推送 (Multicast)"], 
    horizontal=True,
    key="制導維度切換器"
)

with st.form("manual_制導form_v41_2", clear_on_submit=False):
    target_uids = ""
    if target_mode == "單人/多人精準推送 (Multicast)":
        target_uids = st.text_input(
            "🆔 請輸入目標好友之 LINE User ID：", 
            value="Uf166c741223bc8ee5d82fd1fd9f4df86",
            placeholder="多個 ID 請用半形逗號隔開，例如: U1234a..., U5678b..."
        )
        
    custom_text = st.text_area("發射內文：", placeholder="在此輸入要手動推送的文字內容...")
    
    if st.form_submit_button("🚀 執行手動精準發射"):
        if custom_text.strip():
            try:
                if target_mode == "全員廣播 (Broadcast)":
                    line_api.broadcast(TextSendMessage(text=f"【手動全員廣播】\n\n{custom_text}"))
                    save_to_history("手動全員廣播", custom_text)
                    st.toast("📢 已成功執行全員廣播發射")
                else:
                    raw_list = target_uids.split(",")
                    id_list = []
                    for uid in raw_list:
                        cleaned_id = uid.strip()
                        if cleaned_id and cleaned_id not in id_list:
                            id_list.append(cleaned_id)
                            
                    if not id_list:
                        st.error("❌ 攔截：未偵測到任何有效的好友 User ID，發射終止. ")
                    else:
                        line_api.multicast(id_list, TextSendMessage(text=f"【手動精準推送】\n\n{custom_text}"))
                        save_to_history("手動精準推送", f"🎯 目標對象: {', '.join(id_list)}\n\n{custom_text}")
                        st.toast(f"🚀 已成功送達指定之 {len(id_list)} 位好友端")
                st.rerun()
            except Exception as line_err: 
                st.error(f"連線異常: {str(line_err)}")

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
        except Exception as e: st.error(f"對接失敗: {str(e)}")

st.markdown("---")

# --- 歷史經文典藏管理庫 ---
st.subheader("📚 歷史經文典藏管理庫")
history_data = []
if os.path.exists(DB_FILE):
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f: history_data = json.load(f)
    except: pass

if history_data:
    html_report_content = """
    <html>
    <head>
        <meta charset='utf-8'>
        <title>每日聖經經文歷史典藏稽核報告</title>
        <style>
            @page { size: A4; margin: 15mm 15mm; }
            body { font-family: 'Microsoft JhengHei', 'Heiti TC', sans-serif; padding: 0; margin: 0; color: #333333; line-height: 1.5; background: #ffffff; }
            h2 { text-align: center; color: #1A237E; border-bottom: 2px solid #1A237E; padding-bottom: 8px; margin-top: 5px; margin-bottom: 20px; font-size: 20px; letter-spacing: 1px; }
            .card { background: #ffffff; padding: 15px; border: 1px solid #e0e0e0; border-left: 6px solid #1A237E; border-radius: 4px; margin-bottom: 15px; box-sizing: border-box; position: relative; page-break-inside: avoid !important; break-inside: avoid !important; }
            .card-auto { border-left-color: #2E7D32; }
            .card-ai { border-left-color: #1565C0; }
            .card-manual { border-left-color: #C62828; }
            .card-multicast { border-left-color: #E65100; }
            .meta { font-size: 12px; color: #555555; margin-bottom: 10px; font-weight: bold; border-bottom: 1px dashed #e0e0e0; padding-bottom: 6px; }
            .badge { padding: 2px 6px; border-radius: 4px; color: #ffffff; font-size: 10px; margin-left: 6px; font-weight: bold; display: inline-block; vertical-align: middle; }
            .badge-auto { background: #2E7D32; }
            .badge-ai { background: #1565C0; }
            .badge-manual { background: #C62828; }
            .badge-multicast { background: #E65100; }
            .content-box { white-space: pre-wrap; word-wrap: break-word; font-family: 'Microsoft JhengHei', sans-serif; font-size: 13.5px; margin: 0; color: #222222; line-height: 1.6; text-align: justify; }
            b { color: #1A237E; font-size: 14px; }
        </style>
    </head>
    <body>
        <h2>🛡️ 每日聖經經文歷史典藏稽核報告</h2>
    """
    for h in history_data:
        raw_cat = h.get('category', '排程推送')
        if "定時" in raw_cat or "排程" in raw_cat:
            std_cat = "排程推送"; css_class = "card-auto"; badge_class = "badge-auto"
        elif "AI" in raw_cat or "智慧" in raw_cat:
            std_cat = "AI智慧廣播"; css_class = "card-ai"; badge_class = "badge-ai"
        elif "精準" in raw_cat or "Multicast" in raw_cat or "🎯" in h.get('content', ''):
            std_cat = "手動精準推送"; css_class = "card-multicast"; badge_class = "badge-multicast"
        else:
            std_cat = "手動全員廣播"; css_class = "card-manual"; badge_class = "badge-manual"
            
        formatted_content = h['content'].replace('【', '<b>【').replace('】', '】</b><br>').strip()
        formatted_content = formatted_content.replace('<br><br>', '<br>')
            
        html_report_content += f"""
        <div class='card {css_class}'>
            <div class='meta'>📅 推送日期: {h['date']} &nbsp;&nbsp;&nbsp;&nbsp; ⏰ 精準時間: {h['time']} &nbsp;&nbsp;&nbsp;&nbsp; 🏷️ 推送類型: <span class='badge {badge_class}'>{std_cat}</span></div>
            <div class='content-box'>{formatted_content}</div>
        </div>
        """
    html_report_content += """
        <script>window.onload = function() { window.print(); }</script>
    </body>
    </html>
    """

    col_dl1, col_dl2 = st.columns([1, 1])
    with col_dl1:
        download_lines = [f"========================================\n日期時間: {h['date']} {h['time']}\n分類標籤: {h['category']}\n----------------------------------------\n{h['content']}\n========================================\n\n" for h in history_data]
        st.download_button(label="📥 下載完整歷史經文 (.txt)", data="".join(download_lines), file_name=f"bible_history_{datetime.now(timezone.utc).astimezone(TZ_TW).strftime('%Y%m%d')}.txt", mime="text/plain")
    with col_dl2:
        st.download_button(label="🖨️ 匯出中文 PDF 報告", data=html_report_content, file_name=f"bible_audit_report_{datetime.now(timezone.utc).astimezone(TZ_TW).strftime('%Y%m%d')}.html", mime="text/html")

    # --- 在這裡插入清理功能 ---
    st.markdown("---") # 加一條分隔線
    with st.expander("⚙️ 進階系統維護"):
        if st.button("⚠️ 強制清除歷史記錄 (重置系統)"):
            if os.path.exists("bible_history.json"): # 確保檔名與您程式中定義的一致
                os.remove("bible_history.json")
                st.warning("歷史記錄已清除，請重新整理頁面。")
                st.rerun()
            else:
                st.info("目前沒有歷史記錄檔案。")
    
    filter_type = st.selectbox("🔍 按推送類型過濾顯示：", ["全部", "排程推送", "手動全員廣播", "手動精準推送", "AI智慧廣播"])
    for item in history_data:
        raw_cat = item['category']
        if "定時" in raw_cat or "排程" in raw_cat: std_cat = "排程推送"; tag_class = "type-tag-auto"
        elif "AI" in raw_cat or "智慧" in raw_cat: std_cat = "AI智慧廣播"; tag_class = "type-tag-ai"
        elif "精準" in raw_cat or "Multicast" in raw_cat: std_cat = "手動精準推送"; tag_class = "type-tag-multicast"
        else: std_cat = "手動全員廣播"; tag_class = "type-tag-manual"
        
        if filter_type != "全部" and std_cat != filter_type: continue
        st.markdown(f'<div class="history-card"><strong>📅 {item["date"]} &nbsp;&nbsp; ⏰ {item["time"]}</strong> &nbsp;&nbsp; <span class="{tag_class}">{std_cat}</span><pre style="white-space: pre-wrap; font-family: sans-serif; background: transparent; border: none; padding: 0; margin-top: 8px; color: #B0BEC5; font-size: 0.8rem;">{item["content"]}</pre></div>', unsafe_allow_html=True)
else: st.info("⚠️ 儲存艙目前尚無歷史保存紀錄。")
