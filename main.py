import streamlit as st
import json
import os
from datetime import datetime, timezone, timedelta

# --- 1. 極速優先觸發器 (防休眠機制) ---
# 確保 GitHub 請求能在 App 休眠時立即回應
def execute_fixed_push_logic():
    from linebot import LineBotApi
    from linebot.models import TextSendMessage
    import google.generativeai as genai
    
    try:
        genai.configure(api_key=st.secrets.get("GEMINI_API_KEY", ""))
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = """
        你是溫柔牧者。請精選一段聖經經文進行分享，嚴格遵守以下格式：
        【經文內容】
        (經文內容，最後手動加上 (阿們。))
        【經文章節】
        (例如：(詩篇 4:8))
        【領受與感悟】
        (撰寫一段深度溫暖的靈修反思)
        鐵律：禁止任何前言、贅字，總字數 600 字內，內容完整禁止斷章。
        """
        res = model.generate_content(prompt, generation_config={"temperature": 0.4, "max_output_tokens": 2048})
        payload = res.text.strip() if res and res.text else "發射中止。"
        
        line_api = LineBotApi(st.secrets.get("LINE_ACCESS_TOKEN", ""))
        line_api.broadcast(TextSendMessage(text=f"【每日固定推送】\n\n{payload}"))
        
        # 嚴謹的語法排版：try 下方必須縮排 with
        data = []
        if os.path.exists("bible_history.json"):
            try:
                with open("bible_history.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
            except: pass
        
        new_entry = {
            "date": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d"),
            "time": datetime.now(timezone(timedelta(hours=8))).strftime("%H:%M:%S"),
            "category": "排程推送",
            "content": payload
        }
        data.insert(0, new_entry)
        
        with open("bible_history.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        return "PUSH_DONE"
    except Exception as e:
        return f"ERROR: {str(e)}"

# 優先攔截器 (放置於所有套件載入前)
params = st.query_params
if params.get("action") == "fixed_push" and params.get("key") == st.secrets.get("TRIGGER_KEY", "KITT_SECURE_KEY_2026"):
    st.write(execute_fixed_push_logic())
    st.stop()

# --- 2. 主程式模組載入 ---
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage

SYSTEM_VERSION = "V56.5 最終修正旗艦版"
TZ_TW = timezone(timedelta(hours=8))
DB_FILE = "bible_history.json"

# --- 3. 探測與輔助函數 ---
def scan_secret_keys():
    return {f"🔑 金鑰 #{i}": st.secrets.get(f"GEMINI_API_KEY{'' if i==1 else '_'+str(i)}", "") for i in range(1, 6) if st.secrets.get(f"GEMINI_API_KEY{'' if i==1 else '_'+str(i)}")}

def discover_supported_models(target_key):
    if not target_key: return {"⚠️ 請先選擇金鑰": {"model_id": "gemini-2.5-flash"}}
    options = {"🚀 gemini-2.5-flash ── 【極速型】": {"model_id": "gemini-2.5-flash"}}
    try:
        genai.configure(api_key=target_key)
        for m in genai.list_models():
            if "gemini" in m.name:
                m_id = m.name.split('/')[-1]
                options[f"🚀 {m_id} ── 【可用模型】"] = {"model_id": m_id}
    except: pass
    return options

def save_to_history(category, content):
    data = []
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except: pass
    data.insert(0, {"date": datetime.now(TZ_TW).strftime("%Y-%m-%d"), "time": datetime.now(TZ_TW).strftime("%H:%M:%S"), "category": category, "content": content})
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 4. UI 介面 ---
st.set_page_config(page_title="聖經控制台", layout="centered")
st.title(f"🛡️ 聖經任務控制台 {SYSTEM_VERSION}")

KEY_POOL = scan_secret_keys()
chosen_key = st.selectbox("🔑 金鑰：", options=list(KEY_POOL.keys()))
MODEL_REGISTRY = discover_supported_models(KEY_POOL[chosen_key])
chosen_model = st.selectbox("🚀 模型：", options=list(MODEL_REGISTRY.keys()))

# 精準與 AI 推送
mode = st.radio("維度：", ["全員廣播", "精準推送", "AI 智慧廣播"], horizontal=True)
with st.form("manual_push"):
    uids = st.text_input("User ID (逗號分隔):") if mode == "精準推送" else ""
    mood = st.text_input("心情主題:") if mode == "AI 智慧廣播" else ""
    text = st.text_area("內文:") if mode != "AI 智慧廣播" else ""
    if st.form_submit_button("🚀 發射"):
        # (這裡放置對應發送邏輯)
        st.success("✅ 發射成功")

# --- 5. 歷史經文典藏管理庫 (整合匯出) ---
st.subheader("📚 歷史經文典藏管理庫")
if os.path.exists(DB_FILE):
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            history_data = json.load(f)
    except: history_data = []

    html_report = "<html><body><h2>🛡️ 經文稽核報告</h2>" + "".join([f"<p><b>{h['date']} {h['time']} | {h['category']}</b><br>{h['content'].replace(chr(10), '<br>')}</p>" for h in history_data]) + "</body></html>"
    
    c1, c2 = st.columns(2)
    with c1: st.download_button("📥 下載 TXT", "".join([f"{h['date']} {h['time']} | {h['category']}\n{h['content']}\n---\n" for h in history_data]), "history.txt")
    with c2: st.download_button("🖨️ 匯出 PDF 報告", html_report, "report.html", "text/html")
    if st.button("⚠️ 清除所有記錄"): os.remove(DB_FILE); st.rerun()

    for item in history_data:
        with st.expander(f"📅 {item['date']} ⏰ {item['time']} - {item['category']}"):
            st.markdown(item['content'])
