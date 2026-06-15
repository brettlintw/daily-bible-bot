import streamlit as st
import json
import os
import time
from datetime import datetime, timezone, timedelta
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 設定 ---
DB_FILE = "bible_history.json"
TZ_TW = timezone(timedelta(hours=8))

st.set_page_config(page_title="靈修控制台", layout="wide")
st.title("🛡️ 聖經-LINE推送 V60.0 版")

# --- 輔助函式 ---
def scan_secret_keys():
    return {f"🔑 金鑰 #{i}": st.secrets.get(f"GEMINI_API_KEY{'' if i==1 else '_'+str(i)}", "") for i in range(1, 6) if st.secrets.get(f"GEMINI_API_KEY{'' if i==1 else '_'+str(i)}")}

def load_history():
    if not os.path.exists(DB_FILE): return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except: return []

# --- UI 設定 ---
KEY_POOL = scan_secret_keys()
chosen_key = st.selectbox("🔑 金鑰：", options=list(KEY_POOL.keys()))

# --- 【臨時增加】群組 ID 獲取器 ---
st.subheader("🛠️ 系統工具")
if st.button("🔍 獲取最近一個群組 ID"):
    st.info("請確保您剛在 LINE 群組傳送過訊息！")
    try:
        line_api = LineBotApi(st.secrets.get("LINE_ACCESS_TOKEN", ""))
        # 由於 Messaging API 沒有直接列出群組的 API，
        # 我們透過檢測最近的一筆互動來抓取
        st.warning("若系統無反應，請確保您已在 LINE 設定中開啟 Webhook 接收。")
        st.code("群組 ID 獲取邏輯需配合 Webhook 監聽，若此處無法直接讀取，請檢查您的 LINE Developer Console。")
    except Exception as e:
        st.error(f"獲取失敗: {e}")

# --- 推送邏輯 ---
mode = st.radio("維度：", ["全員廣播", "精準推送", "AI 智慧廣播"], horizontal=True)
with st.form("push_form"):
    uids = st.text_input("User ID 或 群組 ID (以 C 開頭):") if mode == "精準推送" else ""
    mood = st.text_input("心情主題:") if mode == "AI 智慧廣播" else ""
    text = st.text_area("內文:") if mode != "AI 智慧廣播" else ""
    
    if st.form_submit_button("🚀 發射"):
        try:
            genai.configure(api_key=KEY_POOL[chosen_key])
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            if mode == "AI 智慧廣播":
                prompt = f"請針對主題「{mood}」，選取一段聖經經文分享。格式：【經文內容】(阿們。)；【經文章節】；【領受與感悟】。"
                content = model.generate_content(prompt).text
            else:
                content = text
            
            line_api = LineBotApi(st.secrets.get("LINE_ACCESS_TOKEN", ""))
            if mode == "全員廣播":
                line_api.broadcast(TextSendMessage(text=content))
            else:
                # 這裡支援 U開頭的 User ID 或 C開頭的 Group ID
                line_api.push_message(uids, TextSendMessage(text=content))
            
            history = load_history()
            history.insert(0, {"date": datetime.now(TZ_TW).strftime("%Y-%m-%d"), "time": datetime.now(TZ_TW).strftime("%H:%M:%S"), "category": mode, "content": content})
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=4)
            st.success("✅ 發射成功")
        except Exception as e:
            st.error(f"❌ 發射失敗: {str(e)}")

# --- 歷史紀錄區 ---
st.subheader("📚 歷史經文典藏管理庫")
history_data = load_history()
if history_data:
    if st.button("⚠️ 清除所有記錄"):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        st.rerun()
    for item in reversed(history_data):
        with st.expander(f"📅 {item['date']} - {item['category']}"): st.markdown(item['content'])
