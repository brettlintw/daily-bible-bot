import streamlit as st
import google.generativeai as genai
from datetime import datetime, timedelta, timezone
import random
import time
import threading
import json
import os

# --- 1. 頁面配置 (V41.2 行動端視覺終極咬合版) ---
st.set_page_config(page_title="聖經控制台 V41.2", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .main .block-container { max-width: 80% !important; padding: 0.3rem 1rem !important; }
    @media (max-width: 1023px) { 
        .main .block-container { max-width: 100% !important; padding: 0.2rem 0.5rem !important; } 
        h1 { font-size: 0.95rem !important; display: flex !important; align-items: center !important; flex-wrap: nowrap !important; }
        .status-tag { font-size: 0.55rem !important; padding: 1px 3px !important; margin-left: 3px !important; white-space: nowrap !important; }
        .schedule-radar-box { padding: 8px !important; }
        .schedule-radar-box code { font-size: 0.85rem !important; word-break: break-all !important; }
    }
    h1 { font-size: 1.15rem !important; color: #E0E0E0; white-space: nowrap !important; }
    .status-tag { font-size: 0.7rem; padding: 2px 8px; border-radius: 10px; background: #00E676; color: black; margin-left: 5px; white-space: nowrap !important; display: inline-block !important; }
    .history-card { background: #1E1E1E; padding: 10px; border-radius: 8px; border-left: 5px solid #00E676; margin-bottom: 8px; color: #E0E0E0; }
    .type-tag-multicast { background: #E65100; color: white; padding: 1px 6px; border-radius: 4px; font-size: 0.65rem; }
    .api-active-tag { background: #E0F2F1; color: #004D40; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; font-weight: bold; white-space: normal !important; word-break: break-all !important; }
    .schedule-radar-box { background: #1A237E; border: 1px solid #00E676; border-radius: 8px; padding: 10px; margin-bottom: 15px; color: #00E676; font-family: monospace; width: 100%; box-sizing: border-box; }
    [data-testid="stHeader"], footer, #MainMenu { visibility: hidden; height: 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心時區與全域時間配置 ---
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
RADAR_TRACK_FILE = "radar_user_track.json"

# --- 3. 金鑰與模型動態探測中樞 ---
def scan_secret_keys():
    key_names = ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3", "GEMINI_API_KEY_4", "GEMINI_API_KEY_5"]
    pool = {f"🔑 金鑰密鑰順位 #{i+1}": get_cfg(n, "") for i, n in enumerate(key_names) if get_cfg(n, "")}
    return pool if pool else {"⚠️ 未偵測到金鑰": ""}

KEY_POOL = scan_secret_keys()

def discover_supported_models(target_key):
    if not target_key: return {"⚠️ 請先選擇有效金鑰": {"model_id": "gemini-2.5-flash", "billing": "免費版"}}
    return {"🚀 gemini-2.5-flash ── [免費版]": {"model_id": "gemini-2.5-flash", "billing": "免費版"}}

# --- 4. 配置與生成核心 ---
def execute_ai_safe_generation(target_model_id, target_api_key, mode="聖經經文", custom_mood=None, custom_persona="暖心"):
    genai.configure(api_key=target_api_key)
    model = genai.GenerativeModel(model_name=target_model_id)
    persona = "你是 K.I.T.T.，冷靜理性。" if custom_persona == "KITT" else "你是溫柔牧者。"
    prompt = f"{persona}\n請依「經文內容/章節/領受與感悟」架構撰寫。總字數嚴格 900 字內，超過即截斷焊接 (省略)。"
    
    res = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(max_output_tokens=2000))
    final_text = str(res.text).strip()
    return final_text[:894] + " (省略)" if len(final_text) > 900 else final_text

def save_to_history(category, content):
    data = []
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: data = json.load(f)
        except: pass
    data.insert(0, {"id": int(time.time()*1000), "date": datetime.now(TZ_TW).strftime("%Y-%m-%d"), "time": datetime.now(TZ_TW).strftime("%H:%M:%S"), "category": category, "content": content})
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

# --- 5. UI 佈局 ---
st.markdown(f"<h1>🛡️ 聖經任務控制台 V41.2 <span class='status-tag'>🛰️ 聯邦制導</span><span class='status-tag' style='background:#1565C0; color:white;'>世紀封頂</span></h1>", unsafe_allow_html=True)

# 排程確認牆
cfg = json.load(open(CONFIG_FILE)) if os.path.exists(CONFIG_FILE) else {"schedule": "09:00"}
st.markdown(f"""<div class="schedule-radar-box">⏰ [排程確認牆]: <code>{cfg.get("schedule", "09:00")}</code></div>""", unsafe_allow_html=True)

# 模式切換與推送中樞
target_mode = st.radio("🎯 模式：", ["全員廣播", "精準推送"], horizontal=True)
with st.form("manual_form"):
    target_uids = st.text_input("User ID:", value="Uf166c741223bc8ee5d82fd1fd9f4df86") if target_mode == "精準推送" else ""
    custom_text = st.text_area("發射內文:")
    if st.form_submit_button("🚀 發射"):
        if target_mode == "精準推送":
            id_list = [i.strip() for i in target_uids.split(",") if i.strip()]
            line_api.multicast(id_list, TextSendMessage(text=custom_text))
        else:
            line_api.broadcast(TextSendMessage(text=custom_text))
        save_to_history(f"手動{target_mode}", custom_text)
        st.toast("發射完成")

# AI 廣播
c1, c2, c3 = st.columns(3)
with c1: mood = st.text_input("心情:", placeholder="心情...")
with c2: persona = st.selectbox("風格:", ["暖心", "專業", "KITT"])
with c3: mode = st.selectbox("格式:", ["聖經經文", "推薦詩歌"])
if st.button("✨ 啟動 AI 廣播"):
    k_val = list(KEY_POOL.values())[0]
    payload = execute_ai_safe_generation("gemini-2.5-flash", k_val, mode, mood, persona)
    line_api.broadcast(TextSendMessage(text=payload))
    save_to_history("AI智慧廣播", payload)
    st.rerun()

# 歷史記錄輸出
st.subheader("📚 歷史經文典藏")
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r", encoding="utf-8") as f: history = json.load(f)
    for item in history:
        st.markdown(f'<div class="history-card"><strong>📅 {item["date"]} {item["time"]}</strong> <pre>{item["content"]}</pre></div>', unsafe_allow_html=True)
