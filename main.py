import streamlit as st
import google.generativeai as genai
from datetime import datetime, timedelta, timezone
import random
import time
import threading
import json
import os

# --- 1. 頁面配置 (行動端視覺咬合 + 標題不折行) ---
st.set_page_config(page_title="聖經控制台 V42.0", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .main .block-container { max-width: 80% !important; padding: 0.3rem 1rem !important; }
    @media (max-width: 1023px) { 
        .main .block-container { max-width: 100% !important; padding: 0.2rem 0.5rem !important; } 
        h1 { font-size: 0.95rem !important; display: flex !important; align-items: center !important; flex-wrap: nowrap !important; }
        .status-tag { font-size: 0.55rem !important; padding: 1px 3px !important; margin-left: 3px !important; white-space: nowrap !important; }
        .schedule-radar-box { padding: 8px !important; }
    }
    h1 { font-size: 1.15rem !important; color: #E0E0E0; white-space: nowrap !important; }
    .history-card { background: #1E1E1E; padding: 10px; border-radius: 8px; border-left: 5px solid #00E676; margin-bottom: 8px; color: #E0E0E0; }
    .schedule-radar-box { background: #1A237E; border: 1px solid #00E676; border-radius: 8px; padding: 10px; margin-bottom: 15px; color: #00E676; font-family: monospace; }
    [data-testid="stHeader"], footer, #MainMenu { visibility: hidden; height: 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心設定 ---
TZ_TW = timezone(timedelta(hours=8))
DB_FILE = "bible_history.json"
CONFIG_FILE = "engine_config.json"
TRIGGER_KEY = "KITT_SECURE_KEY_2026"

# --- 3. 印刷級 PDF 輸出 (滿足指標 5, 11) ---
def get_pdf_html_content(history_data):
    html = """<html><head><meta charset="utf-8">
    <style>
        @page { size: A4; margin: 20mm; }
        body { font-family: 'Microsoft JhengHei', sans-serif; line-height: 1.8; color: #000; }
        .record { border-bottom: 2px solid #333; padding: 25px 0; page-break-inside: avoid; }
        .meta { font-size: 12px; font-weight: bold; color: #444; background: #f0f0f0; padding: 5px; }
        .content { white-space: pre-wrap; font-size: 15px; margin-top: 10px; }
    </style></head><body><h2>經文典藏稽核報告</h2>"""
    for h in history_data:
        html += f'<div class="record"><div class="meta">日期：{h["date"]} {h["time"]} | 類型：{h["category"]}</div><div class="content">{h["content"]}</div></div>'
    html += "</body></html>"
    return html

# --- 4. 核心邏輯 (滿足指標 2, 3, 4, 6) ---
def execute_ai_safe_generation(target_model_id, target_api_key, mode="聖經經文", custom_mood=None, custom_persona="暖心"):
    genai.configure(api_key=target_api_key)
    model = genai.GenerativeModel(model_name=target_model_id)
    persona = "你是 K.I.T.T.，冷靜理性。" if custom_persona == "KITT" else "你是溫柔牧者。"
    prompt = f"{persona}\n請依「經文內容/章節/領受與感悟」架構撰寫。總字數嚴格控制在 900 中文字內。最後以句號結束。"
    
    res = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(max_output_tokens=2000))
    final_text = str(res.text).strip()
    return final_text[:894] + " (省略)" if len(final_text) > 900 else final_text

def save_to_history(category, content):
    data = []
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: data = json.load(f)
        except: pass
    data.insert(0, {"date": datetime.now(TZ_TW).strftime("%Y-%m-%d"), "time": datetime.now(TZ_TW).strftime("%H:%M:%S"), "category": category, "content": content})
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

# --- 5. UI 與排程管理 (滿足指標 7, 8, 9) ---
st.markdown("<h1>🛡️ 聖經任務控制台 V42.0</h1>", unsafe_allow_html=True)

# 排程確認牆 (指標 9)
cfg = json.load(open(CONFIG_FILE)) if os.path.exists(CONFIG_FILE) else {"schedule": "09:00"}
st.markdown(f"""<div class="schedule-radar-box">⏰ [排程確認牆]: <code>{cfg.get("schedule", "09:00")}</code></div>""", unsafe_allow_html=True)

# 模式切換鈕 (指標 8)
target_mode = st.radio("🎯 模式：", ["全員廣播", "精準推送"], horizontal=True)
with st.form("manual_form"):
    target_uids = st.text_input("User ID (多個用半形逗號隔開):", value="Uf166c741223bc8ee5d82fd1fd9f4df86") if target_mode == "精準推送" else ""
    custom_text = st.text_area("發射內文:")
    if st.form_submit_button("🚀 發射"):
        if target_mode == "精準推送":
            id_list = [i.strip() for i in target_uids.split(",") if i.strip()]
            line_api.multicast(id_list, TextSendMessage(text=custom_text))
        else:
            line_api.broadcast(TextSendMessage(text=custom_text))
        save_to_history(f"手動{target_mode}", custom_text)
        st.toast("發射完成")

# 歷史記錄輸出 (指標 5, 11)
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r", encoding="utf-8") as f: history = json.load(f)
    st.download_button("🖨️ 下載精準排版 PDF 報告", data=get_pdf_html_content(history), file_name="bible_report.html", mime="text/html")
    for item in history:
        tag = "✅ 排程" if "排程" in item['category'] else "🤖 AI" if "AI" in item['category'] else "🎯 精準" if "精準" in item['category'] else "📢 全員"
        st.markdown(f'<div class="history-card"><strong>📅 {item["date"]} {item["time"]} | {tag}</strong><pre>{item["content"]}</pre></div>', unsafe_allow_html=True)
