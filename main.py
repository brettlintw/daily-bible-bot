import streamlit as st
import google.generativeai as genai
from datetime import datetime, timedelta, timezone, date
import threading
import json
import os
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 1. 系統宣告與環境初始化 ---
SYSTEM_VERSION = "V52.4 全能旗艦版 (含金鑰探測)"
TZ_TW = timezone(timedelta(hours=8))
DB_FILE = "bible_history.json"
CONFIG_FILE = "engine_config.json"

def get_cfg(key, fallback):
    try: return st.secrets.get(key, fallback) or fallback
    except: return fallback

LINE_TOKEN = get_cfg("LINE_ACCESS_TOKEN", "")
line_api = LineBotApi(LINE_TOKEN)

# --- 2. 核心探測模組 (恢復保留) ---
def scan_secret_keys():
    key_names = ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3", "GEMINI_API_KEY_4", "GEMINI_API_KEY_5"]
    pool = {}
    for idx, name in enumerate(key_names, start=1):
        v = get_cfg(name, "")
        if v and len(v) > 5:
            masked_key = f"***{v[-4:]}"
            pool[f"🔑 金鑰密鑰順位 #{idx} ({masked_key})"] = v
    if not pool: pool["⚠️ 未偵測到有效 Key"] = ""
    return pool

KEY_POOL = scan_secret_keys()

def discover_supported_models(target_key):
    if not target_key: return {"⚠️ 請先選擇金鑰": {"model_id": "gemini-2.5-flash", "billing": "免費版"}}
    util_registry = {
        "gemini-2.5-flash": "【極速型】", "gemini-2.5-pro": "【推理型】",
        "gemini-1.5-pro": "【長記憶型】", "gemini-1.5-flash": "【穩健型】"
    }
    discovered_options = {}
    try:
        genai.configure(api_key=target_key)
        for m_id in util_registry.keys():
            if any(m_id in m.name for m in genai.list_models()):
                discovered_options[f"🚀 {m_id} ── {util_registry[m_id]}"] = {"model_id": m_id}
    except: pass
    if not discovered_options: discovered_options["🚀 gemini-2.5-flash ── [保底核心]"] = {"model_id": "gemini-2.5-flash"}
    return discovered_options

# --- 3. 核心功能函式 ---
def load_engine_config():
    default_config = {"daily_schedule": "09:00,12:00,21:00", "fixed_model_id": "gemini-2.5-flash"}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f: return {**default_config, **json.load(f)}
        except: pass
    return default_config

def execute_ai_safe_generation(target_model_id, target_api_key, custom_mood="", custom_persona="暖心"):
    genai.configure(api_key=target_api_key)
    model = genai.GenerativeModel(model_name=target_model_id)
    prompt = f"你是{custom_persona}牧者。{f'心情主題:{custom_mood}' if custom_mood else ''} 請精選聖經經文並深度反思。內容務必完整，請勿中斷。"
    res = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(max_output_tokens=4096))
    return res.text if res else "發射中止。"

def execute_fixed_push():
    config = load_engine_config()
    output = execute_ai_safe_generation(config.get("fixed_model_id"), config.get("fixed_key_val") or get_cfg("GEMINI_API_KEY", ""))
    line_api.broadcast(TextSendMessage(text=f"【每日固定推送】\n\n{output}"))
    save_to_history("排程推送", output)

def save_to_history(category, content):
    current_tw = datetime.now(TZ_TW)
    data = []
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: data = json.load(f)
        except: pass
    data.insert(0, {"date": current_tw.strftime("%Y-%m-%d"), "time": current_tw.strftime("%H:%M:%S"), "category": category, "content": content})
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

# --- 4. 外部觸發與 UI ---
params = st.query_params
if params.get("action") == "fixed_push" and params.get("key") == get_cfg("TRIGGER_KEY", "KITT_SECURE_KEY_2026"):
    execute_fixed_push()
    st.write("PUSH_DONE")
    st.stop()

st.set_page_config(page_title="聖經控制台", layout="centered")
st.title(f"🛡️ 聖經任務控制台 {SYSTEM_VERSION}")

# 金鑰與模型選擇
chosen_key_label = st.selectbox("請選擇金鑰：", options=list(KEY_POOL.keys()))
CURRENT_KEY = KEY_POOL[chosen_key_label]
MODEL_REGISTRY = discover_supported_models(CURRENT_KEY)
chosen_model_label = st.selectbox("請選擇模型：", options=list(MODEL_REGISTRY.keys()))
CURRENT_MODEL = MODEL_REGISTRY[chosen_model_label]["model_id"]

# AI 智慧廣播與精準推送區塊 (同上)
st.subheader("🤖 AI 智慧廣播 / 🎯 精準推送")
if st.button("✨ 啟動 AI 廣播"):
    payload = execute_ai_safe_generation(CURRENT_MODEL, CURRENT_KEY)
    line_api.broadcast(TextSendMessage(text=f"【AI智慧廣播】\n\n{payload}"))
    save_to_history("AI智慧廣播", payload)
    st.success("成功")


# ---5. 歷史經文典藏管理庫 (V43.1 精簡互動版) ---
st.subheader("📚 歷史經文典藏管理庫")
history_data = []
if os.path.exists(DB_FILE):
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f: history_data = json.load(f)
    except: pass

if history_data:
    # 1. 完整且專業的 PDF/HTML 樣式生成模組 (保留原本設計)
    html_report_content = """
    <html><head><meta charset='utf-8'>
    <style>
        @page { size: A4; margin: 15mm; }
        body { font-family: 'Microsoft JhengHei', sans-serif; line-height: 1.6; }
        .card { border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; border-radius: 8px; }
        .meta { font-weight: bold; color: #1A237E; border-bottom: 1px dotted #ccc; margin-bottom: 5px; }
    </style></head>
    <body><h2>🛡️ 每日聖經經文稽核報告</h2>"""
    for h in history_data:
        html_report_content += f"<div class='card'><div class='meta'>📅 {h['date']} ⏰ {h['time']} | 類型: {h['category']}</div><div>{h['content'].replace(chr(10), '<br>')}</div></div>"
    html_report_content += "</body></html>"

    # 2. 功能按鈕區
    col_dl1, col_dl2 = st.columns([1, 1])
    with col_dl1:
        download_lines = [f"日期: {h['date']} {h['time']}\n類型: {h['category']}\n內容: {h['content']}\n---\n" for h in history_data]
        st.download_button("📥 下載完整歷史經文 (.txt)", "".join(download_lines), "bible_history.txt")
    with col_dl2:
        st.download_button("🖨️ 匯出中文 PDF 報告", data=html_report_content, file_name="bible_audit_report.html", mime="text/html")

    # 3. 系統維護區
    if st.button("⚠️ 強制清除歷史記錄"):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        st.rerun()

    st.markdown("---")
    
    # 4. 分類索引列表 (只顯示標題與詳情展開)
    filter_type = st.selectbox("🔍 按推送類型過濾顯示：", ["全部", "排程推送", "手動全員廣播", "手動精準推送", "AI智慧廣播"])

    for item in history_data:
        raw_cat = item.get('category', '')
        # 標籤映射
        if "定時" in raw_cat or "排程" in raw_cat: std_cat = "排程推送"; tag_class = "type-tag-auto"
        elif "AI" in raw_cat or "智慧" in raw_cat: std_cat = "AI智慧廣播"; tag_class = "type-tag-ai"
        elif "精準" in raw_cat or "Multicast" in raw_cat: std_cat = "手動精準推送"; tag_class = "type-tag-multicast"
        else: std_cat = "手動全員廣播"; tag_class = "type-tag-manual"
        
        if filter_type != "全部" and std_cat != filter_type: continue
        
        # 提取索引標題 (取經文的前幾行或標題)
        content_preview = item['content'].split('\n')[0][:50] + "..." 
        
        # 使用 expander 實現「詳情」按鈕功能
        with st.expander(f"📅 {item['date']} &nbsp;&nbsp; ⏰ {item['time']} &nbsp;&nbsp; <span class='{tag_class}'>{std_cat}</span>", expanded=False):
            st.markdown(f"**【摘要】** {content_preview}")
            st.markdown("---")
            st.markdown(f"**【完整內容】**\n\n{item['content']}")
            
else:
    st.info("⚠️ 儲存艙目前尚無歷史保存紀錄。")
    
