import streamlit as st
import google.generativeai as genai
from datetime import datetime, timedelta, timezone, date
import threading
import json
import os
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 1. 系統宣告與環境初始化 ---
SYSTEM_VERSION = "V52.3 最終修復版"
TZ_TW = timezone(timedelta(hours=8))
DB_FILE = "bible_history.json"
CONFIG_FILE = "engine_config.json"

def get_cfg(key, fallback):
    try: return st.secrets.get(key, fallback) or fallback
    except: return fallback

LINE_TOKEN = get_cfg("LINE_ACCESS_TOKEN", "")
line_api = LineBotApi(LINE_TOKEN)

# --- 2. 必須放在最前面的函式定義 ---
def load_engine_config():
    default_config = {"daily_schedule": "09:00,12:00,21:00", "fixed_model_id": "gemini-2.5-flash"}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**default_config, **data}
        except: pass
    return default_config

def save_to_history(category, content):
    current_tw = datetime.now(TZ_TW)
    new_entry = {"date": current_tw.strftime("%Y-%m-%d"), "time": current_tw.strftime("%H:%M:%S"), "category": category, "content": content}
    data = []
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: data = json.load(f)
        except: pass
    data.insert(0, new_entry)
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def execute_ai_safe_generation(target_model_id, target_api_key, mode="聖經經文", custom_mood="", custom_persona="暖心"):
    genai.configure(api_key=target_api_key)
    model = genai.GenerativeModel(model_name=target_model_id)
    prompt = f"你是{custom_persona}牧者。{f'心情主題是:{custom_mood}' if custom_mood else ''} 請精選聖經經文並深度反思。內容務必完整，請勿中斷。"
    res = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(max_output_tokens=4096))
    return res.text if res else "發射中止。"

def execute_fixed_push():
    config = load_engine_config()
    output = execute_ai_safe_generation(
        target_model_id=config.get("fixed_model_id", "gemini-2.5-flash"), 
        target_api_key=config.get("fixed_key_val") or get_cfg("GEMINI_API_KEY", ""), 
        mode="聖經經文"
    )
    line_api.broadcast(TextSendMessage(text=f"【每日固定推送】\n\n{output}"))
    save_to_history("排程推送", output)

# --- 3. 外部觸發入口 ---
params = st.query_params
if params.get("action") == "fixed_push" and params.get("key") == get_cfg("TRIGGER_KEY", "KITT_SECURE_KEY_2026"):
    execute_fixed_push()
    st.write("PUSH_DONE")
    st.stop()

# --- 4. UI 介面 ---
st.set_page_config(page_title=f"聖經控制台 {SYSTEM_VERSION}", layout="centered")
st.title(f"🛡️ 聖經任務控制台 {SYSTEM_VERSION}")

cfg = load_engine_config()
st.subheader("⏰ 每日固定推送監控")
st.info(f"自動化來源：GitHub Actions (Cron)\n設定時段：{cfg.get('daily_schedule')}")

st.subheader("🎯 手動精準推送中樞")
target_mode = st.radio("請選擇發射維度：", ["全員廣播 (Broadcast)", "單人/多人精準推送 (Multicast)"], horizontal=True)

with st.form("manual_push_form"):
    target_uids = ""
    if target_mode == "單人/多人精準推送 (Multicast)":
        target_uids = st.text_input("輸入目標 LINE User ID (逗號分隔):")
    custom_text = st.text_area("發射內文：")
    
    if st.form_submit_button("🚀 執行發射"):
        try:
            if target_mode == "全員廣播 (Broadcast)":
                line_api.broadcast(TextSendMessage(text=custom_text))
                save_to_history("手動全員廣播", custom_text)
            else:
                id_list = [i.strip() for i in target_uids.split(",") if i.strip()]
                line_api.multicast(id_list, TextSendMessage(text=custom_text))
                save_to_history("手動精準推送", custom_text)
            st.success("✅ 發射成功")
        except Exception as e: st.error(f"發射失敗: {str(e)}")

st.subheader("🤖 AI 智慧廣播")
c1, c2 = st.columns(2)
with c1: mood_input = st.text_input("心情主題：")
with c2: persona = st.selectbox("演繹風格：", ["暖心", "專業", "KITT"])

if st.button("✨ 啟動 AI 廣播"):
    payload = execute_ai_safe_generation(cfg.get("fixed_model_id"), get_cfg("GEMINI_API_KEY", ""), custom_mood=mood_input, custom_persona=persona)
    line_api.broadcast(TextSendMessage(text=f"【AI智慧廣播】\n\n{payload}"))
    save_to_history("AI智慧廣播", payload)
    st.success("✨ 廣播發射成功")

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
    
    # ---14. LINE API 狀態診斷小工具 ---
if st.button("🛠️ 測試 LINE 連線狀態"):
    try:
        # 直接呼叫 API 取得機器人資訊
        profile = line_api.get_bot_info()
        st.success(f"✅ 連線成功！您的機器人名稱是: {profile.display_name}")
    except Exception as e:
        st.error(f"❌ 連線失敗！錯誤訊息: {str(e)}")

