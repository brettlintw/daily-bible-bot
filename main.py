import streamlit as st
import google.generativeai as genai
from datetime import datetime, timedelta, timezone, date
import json
import os
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 1. 系統宣告 ---
SYSTEM_VERSION = "V53.1 全能旗艦最終整合版"
TZ_TW = timezone(timedelta(hours=8))
DB_FILE = "bible_history.json"
CONFIG_FILE = "engine_config.json"

def get_cfg(key, fallback):
    try: return st.secrets.get(key, fallback) or fallback
    except: return fallback

line_api = LineBotApi(get_cfg("LINE_ACCESS_TOKEN", ""))

# --- 2. 金鑰與模型探測模組 ---
def scan_secret_keys():
    key_names = ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3", "GEMINI_API_KEY_4", "GEMINI_API_KEY_5"]
    pool = {}
    for idx, name in enumerate(key_names, start=1):
        v = get_cfg(name, "")
        if v and len(v) > 5:
            pool[f"🔑 金鑰 #{idx} (***{v[-4:]})"] = v
    if not pool: pool["⚠️ 未偵測到有效 Key"] = ""
    return pool

def discover_supported_models(target_key):
    if not target_key: return {"⚠️ 請先選擇金鑰": {"model_id": "gemini-2.5-flash"}}
    discovered_options = {"🚀 gemini-2.5-flash ── 【極速型】": {"model_id": "gemini-2.5-flash"}}
    try:
        genai.configure(api_key=target_key)
        for m in genai.list_models():
            if "gemini" in m.name:
                m_id = m.name.split('/')[-1]
                discovered_options[f"🚀 {m_id} ── 【可用模型】"] = {"model_id": m_id}
    except: pass
    return discovered_options

# --- 3. 不斷文生成與紀錄核心 ---
def execute_ai_safe_generation(target_model_id, target_api_key, custom_mood="", custom_persona="暖心"):
    genai.configure(api_key=target_api_key)
    model = genai.GenerativeModel(model_name=target_model_id)
    prompt = f"""
    你是{custom_persona}牧者。{f'心情主題:{custom_mood}' if custom_mood else ''} 請精選聖經經文分享，格式如下：
    【經文內容】
    (經文，最後加上 (阿們。))
    【經文章節】
    (例如：(詩篇 4:8))
    【領受與感悟】
    (深度靈修反思)
    鐵律：禁止引言贅字，總字數 600 字內，內容完整禁止斷章。
    """
    res = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.4, max_output_tokens=2048))
    return res.text.strip() if res and res.text else "發射中止。"

def save_to_history(category, content):
    current_tw = datetime.now(TZ_TW)
    data = []
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: data = json.load(f)
        except: pass
    data.insert(0, {"date": current_tw.strftime("%Y-%m-%d"), "time": current_tw.strftime("%H:%M:%S"), "category": category, "content": content})
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

# --- 4. 外部觸發入口 (GitHub Actions) ---
params = st.query_params
if params.get("action") == "fixed_push" and params.get("key") == get_cfg("TRIGGER_KEY", "KITT_SECURE_KEY_2026"):
    output = execute_ai_safe_generation("gemini-2.5-flash", get_cfg("GEMINI_API_KEY", ""))
    line_api.broadcast(TextSendMessage(text=f"【每日固定推送】\n\n{output}"))
    save_to_history("排程推送", output)
    st.write("PUSH_DONE"); st.stop()

# --- 5. UI 介面 ---
st.set_page_config(page_title="聖經控制台", layout="centered")
st.title(f"🛡️ 聖經任務控制台 {SYSTEM_VERSION}")

KEY_POOL = scan_secret_keys()
chosen_key = st.selectbox("🔑 金鑰：", options=list(KEY_POOL.keys()))
MODEL_REGISTRY = discover_supported_models(KEY_POOL[chosen_key])
chosen_model = st.selectbox("🚀 模型：", options=list(MODEL_REGISTRY.keys()))

mode = st.radio("維度：", ["全員廣播", "精準推送", "AI 智慧廣播"], horizontal=True)
with st.form("manual_push"):
    uids = st.text_input("User ID (逗號分隔):") if mode == "精準推送" else ""
    mood = st.text_input("心情主題:") if mode == "AI 智慧廣播" else ""
    text = st.text_area("內文:") if mode != "AI 智慧廣播" else ""
    if st.form_submit_button("🚀 發射"):
        if mode == "AI 智慧廣播":
            payload = execute_ai_safe_generation(MODEL_REGISTRY[chosen_model]["model_id"], KEY_POOL[chosen_key], mood)
            line_api.broadcast(TextSendMessage(text=payload)); save_to_history("AI智慧廣播", payload)
        elif mode == "全員廣播":
            line_api.broadcast(TextSendMessage(text=text)); save_to_history("手動全員廣播", text)
        else:
            line_api.multicast([i.strip() for i in uids.split(",")], TextSendMessage(text=text)); save_to_history("手動精準推送", text)
        st.success("✅ 發射成功")

# --- 6. 歷史經文典藏管理庫 (整合匯出功能) ---
st.subheader("📚 歷史經文典藏管理庫")
if os.path.exists(DB_FILE):
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f: history_data = json.load(f)
    except: history_data = []

    html_report = "<html><body><h2>🛡️ 經文稽核報告</h2>"
    for h in history_data:
        html_report += f"<div style='border:1px solid #ccc; padding:10px; margin-bottom:10px;'><b>{h['date']} {h['time']} | {h['category']}</b><br>{h['content'].replace(chr(10), '<br>')}</div>"
    html_report += "</body></html>"
    
    c1, c2 = st.columns(2)
    with c1: st.download_button("📥 下載 TXT", "".join([f"{h['date']} {h['time']} | {h['category']}\n{h['content']}\n---\n" for h in history_data]), "history.txt")
    with c2: st.download_button("🖨️ 匯出 PDF 報告", html_report, "report.html", "text/html")
    if st.button("⚠️ 清除記錄"): os.remove(DB_FILE); st.rerun()

    for item in history_data:
        with st.expander(f"📅 {item['date']} ⏰ {item['time']} - {item['category']}"):
            st.markdown(item['content'])
