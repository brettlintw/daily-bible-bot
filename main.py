import streamlit as st
import json
import os
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage
from datetime import datetime, timezone, timedelta

# --- 設定 ---
DB_FILE = "bible_history.json"
TZ_TW = timezone(timedelta(hours=8))
DEFAULT_TARGET_ID = "C43e597148c27a296e67e91d848773957"

st.set_page_config(page_title="靈修控制台", layout="wide")
st.title("🛡️ 聖經-LINE推送 V60.2 最終完整版")

# --- 輔助函式 ---
def load_history():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return []
    return []

# --- 1. 自動發現與設定金鑰與 Token ---
def get_secret(key_name):
    # 優先從 Streamlit Secrets 讀取，若無則從系統環境變數讀取
    return st.secrets.get(key_name, os.environ.get(key_name, ""))

# 抓取 Token (增加手動備援輸入框)
raw_line_token = get_secret("LINE_TOKEN")

st.sidebar.header("⚙️ 系統自動配置")
line_token = st.sidebar.text_input("LINE Token (自動載入):", value=raw_line_token, type="password")

# 自動掃描多組 Gemini Keys
api_key_options = {f"🔑 金鑰 #{i}": get_secret(f"GEMINI_API_KEY{'' if i==1 else '_'+str(i)}") 
                   for i in range(1, 6) if get_secret(f"GEMINI_API_KEY{'' if i==1 else '_'+str(i)}")}

if not api_key_options:
    st.sidebar.error("⚠️ 未偵測到 GEMINI_API_KEY，請檢查 Secrets")
    api_key = ""
    selected_model = "gemini-2.5-flash"
else:
    selected_key_name = st.sidebar.selectbox("選擇 API 金鑰", list(api_key_options.keys()))
    api_key = api_key_options[selected_key_name]
    
    # 動態發現模型
    try:
        genai.configure(api_key=api_key)
        models = [m.name for m in genai.list_models() if "gemini" in m.name]
        selected_model = st.sidebar.selectbox("選擇 AI 模型", models)
    except:
        selected_model = "gemini-2.5-flash"

if not line_token:
    st.sidebar.warning("⚠️ LINE Token 未載入")
else:
    st.sidebar.success("✅ LINE Token 已載入")

# --- 2. 手動精準推送 ---
st.subheader("🚀 手動精準推送")
col1, col2 = st.columns([2, 1])

with col1:
    target_id = st.text_input("目標 UserID / 群組 ID", value=DEFAULT_TARGET_ID)
    theme = st.selectbox("選擇主題", ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"])
    
    if st.button("執行推送"):
        # 強制邏輯：如果 ID 為空，直接擋下，解決 400 Bad Request
        if not target_id or target_id.strip() == "":
            st.error("❌ 目標 ID 不可為空！請填入正確的群組 ID。")
        elif not all([api_key, line_token]):
            st.error("❌ 請確認 API Key、Token 與目標 ID 皆已填寫")
        else:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(selected_model)
                res = model.generate_content(f"請針對「{theme}」主題分享聖經經文。格式：【經文內容】；【章節】；【感悟】")
                
                line_api = LineBotApi(line_token.strip())
                line_api.push_message(target_id.strip(), TextSendMessage(text=f'【靈修分享】\n\n{res.text.strip()}'))
                
                # 寫入歷史 (含 .get 防崩潰)
                history = load_history()
                history.insert(0, {
                    "date": datetime.now(TZ_TW).strftime("%Y-%m-%d"), 
                    "time": datetime.now(TZ_TW).strftime("%H:%M:%S"), 
                    "category": theme, 
                    "content": res.text.strip()
                })
                with open(DB_FILE, "w", encoding="utf-8") as f:
                    json.dump(history, f, ensure_ascii=False, indent=4)
                st.success("✅ 發送成功")
            except Exception as e:
                st.error(f"❌ 發送失敗: {str(e)}")

# --- 3. 展開式歷史管理 (已加入容錯機制) ---
st.subheader("📚 歷史經文典藏管理庫")
history_data = load_history()

if history_data:
    txt_content = "\n\n".join([
        f"{h.get('date', '無日期')} | {h.get('category', '無分類')}\n{h.get('content', '無內容')}" 
        for h in history_data
    ])
    st.download_button("📥 下載完整紀錄 (TXT)", txt_content, file_name="bible_history.txt")

    for i, h in enumerate(history_data):
        title = f"📅 {h.get('date', '無日期')} {h.get('time', '')} | {h.get('category', '無分類')}"
        with st.expander(title):
            st.markdown(h.get('content', '無內容'))
else:
    st.write("目前尚無歷史紀錄。")
