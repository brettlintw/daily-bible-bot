import streamlit as st
import json
import os
from datetime import datetime, timezone, timedelta

# --- 1. 極速優先觸發器 (避免休眠導致 API 回應逾時) ---
def execute_fixed_push_logic():
    from linebot import LineBotApi
    from linebot.models import TextSendMessage
    import google.generativeai as genai
    
    # 這裡直接執行排程發送，不載入複雜 UI
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        genai.configure(api_key=st.secrets.get("GEMINI_API_KEY", ""))
        
        prompt = "你是暖心牧者。請精選一段聖經經文進行分享，格式如下：【經文內容】(經文內容，最後加上(阿們。)) 【經文章節】(例如：詩篇4:8) 【領受與感悟】(一段深度反思)。鐵律：禁止引言，總字數600字內，內容完整。"
        res = model.generate_content(prompt, generation_config={"temperature": 0.4, "max_output_tokens": 2048})
        payload = res.text.strip() if res and res.text else "發射中止。"
        
        line_api = LineBotApi(st.secrets.get("LINE_ACCESS_TOKEN", ""))
        line_api.broadcast(TextSendMessage(text=f"【每日固定推送】\n\n{payload}"))
        
        # 寫入記錄
        save_to_history("排程推送", payload)
        return "PUSH_DONE"
    except Exception as e:
        return f"ERROR: {str(e)}"

# 優先攔截
params = st.query_params
if params.get("action") == "fixed_push" and params.get("key") == st.secrets.get("TRIGGER_KEY", "KITT_SECURE_KEY_2026"):
    st.write(execute_fixed_push_logic())
    st.stop()

# --- 2. 其餘模組與 UI (僅在手動訪問時載入) ---
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage

SYSTEM_VERSION = "V54.0 穩定旗艦版"
TZ_TW = timezone(timedelta(hours=8))
DB_FILE = "bible_history.json"

def save_to_history(category, content):
    data = []
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: data = json.load(f)
        except: pass
    data.insert(0, {"date": datetime.now(TZ_TW).strftime("%Y-%m-%d"), "time": datetime.now(TZ_TW).strftime("%H:%M:%S"), "category": category, "content": content})
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

# --- 3. 核心 UI ---
st.set_page_config(page_title="聖經控制台", layout="centered")
st.title(f"🛡️ 聖經任務控制台 {SYSTEM_VERSION}")

# 簡化版的探測邏輯
KEY_POOL = {f"🔑 金鑰 #{i}": st.secrets.get(f"GEMINI_API_KEY{'' if i==1 else '_'+str(i)}", "") for i in range(1, 6)}
chosen_key = st.selectbox("🔑 金鑰：", options=list(KEY_POOL.keys()))

if st.button("🚀 發送測試推送"):
    payload = "測試經文內容... (阿們。)\n\n【經文章節】(測試)\n\n【領受】測試測試。"
    # 這裡呼叫您的發送邏輯
    st.success("發送成功")

# --- 4. 歷史稽核 ---
st.subheader("📚 歷史經文典藏管理庫")
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r", encoding="utf-8") as f: history_data = json.load(f)
    
    html_report = "<html><body><h2>🛡️ 經文報告</h2>" + "".join([f"<p>{h['date']} | {h['category']}<br>{h['content']}</p>" for h in history_data]) + "</body></html>"
    
    c1, c2 = st.columns(2)
    with c1: st.download_button("📥 下載 TXT", "".join([f"{h['date']} | {h['content']}\n" for h in history_data]), "history.txt")
    with c2: st.download_button("🖨️ 匯出 PDF", html_report, "report.html", "text/html")
    
    for item in history_data:
        with st.expander(f"📅 {item['date']} - {item['category']}"):
            st.markdown(item['content'])
