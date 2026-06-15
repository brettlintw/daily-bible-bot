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
st.title("🛡️ 聖經-LINE推送 V60.2 版")

# --- 輔助函式 ---
def load_history():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return []
    return []

# --- 側邊欄：自動化配置 ---
st.sidebar.header("⚙️ 系統配置")
# 自動讀取 Secrets
api_key = st.sidebar.text_input("Gemini API Key", value=st.secrets.get("GEMINI_API_KEY", ""), type="password")
line_token = st.sidebar.text_input("LINE Token", value=st.secrets.get("LINE_TOKEN", ""), type="password")

# 模型選擇器
def get_model_options():
    return ["gemini-2.5-flash", "gemini-1.5-pro"]

selected_model = st.sidebar.selectbox("選擇 AI 模型", get_model_options())

# --- 主畫面：推送控制台 ---
st.subheader("🚀 手動精準推送")
col1, col2 = st.columns([2, 1])

with col1:
    target_id = st.text_input("目標 UserID / 群組 ID", value=DEFAULT_TARGET_ID)
    theme = st.selectbox("選擇主題", ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"])
    
    if st.button("執行推送"):
        if not all([api_key, line_token, target_id]):
            st.error("請確認 API Key 與 Token 已載入")
        else:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(selected_model)
                res = model.generate_content(f"請針對「{theme}」主題分享聖經經文。格式：【經文內容】；【章節】；【感悟】")
                
                line_api = LineBotApi(line_token)
                line_api.push_message(target_id, TextSendMessage(text=f'【靈修分享】\n\n{res.text.strip()}'))
                
                # 寫入歷史
                history = load_history()
                history.insert(0, {"date": datetime.now(TZ_TW).strftime("%Y-%m-%d"), "time": datetime.now(TZ_TW).strftime("%H:%M:%S"), "category": theme, "content": res.text.strip()})
                with open(DB_FILE, "w", encoding="utf-8") as f:
                    json.dump(history, f, ensure_ascii=False, indent=4)
                st.success("✅ 發送成功")
            except Exception as e:
                st.error(f"❌ 發生錯誤: {str(e)}")

# --- 歷史紀錄庫 (展開式管理庫) ---
st.subheader("📚 歷史經文典藏管理庫")
history_data = load_history()

if history_data:
    if st.download_button("📥 下載完整紀錄 (TXT)", "\n\n".join([f"{h['date']} | {h['category']}\n{h['content']}" for h in history_data]), file_name="bible_history.txt"):
        st.toast("下載中...")

    for i, h in enumerate(history_data):
        with st.expander(f"📅 {h.get('date')} {h.get('time', '')} | {h.get('category')}"):
            st.markdown(h.get('content', ''))
else:
    st.write("目前尚無歷史紀錄。")
