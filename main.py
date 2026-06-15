import streamlit as st
import json
import os
from datetime import datetime, timezone, timedelta
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 設定 ---
DB_FILE = "bible_history.json"
TZ_TW = timezone(timedelta(hours=8))

st.set_page_config(page_title="靈修控制台", layout="wide")
st.title("🛡️ 聖經-LINE推送 V60.1 正式版")

def load_history():
    if not os.path.exists(DB_FILE): return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except: return []

# --- 推送邏輯 ---
mode = st.radio("維度：", ["全員廣播", "精準推送/群組推送", "AI 智慧廣播"], horizontal=True)
with st.form("push_form"):
    uids = st.text_input("User ID 或 Group ID (逗號分隔):") if mode == "精準推送/群組推送" else ""
    mood = st.text_input("心情主題:") if mode == "AI 智慧廣播" else ""
    text = st.text_area("內文:") if mode != "AI 智慧廣播" else ""
    
    if st.form_submit_button("🚀 發射"):
        try:
            line_api = LineBotApi(st.secrets["LINE_ACCESS_TOKEN"])
            
            if mode == "AI 智慧廣播":
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-2.5-flash')
                prompt = f"請針對主題「{mood}」，選取一段聖經經文分享。格式：【經文內容】(阿們。)；【經文章節】；【領受與感悟】。"
                content = model.generate_content(prompt).text
            else:
                content = text
            
            if mode == "全員廣播":
                line_api.broadcast(TextSendMessage(text=content))
            else:
                target_ids = [uid.strip() for uid in uids.split(',')]
                for tid in target_ids:
                    line_api.push_message(tid, TextSendMessage(text=content))
            
            history = load_history()
            history.insert(0, {"date": datetime.now(TZ_TW).strftime("%Y-%m-%d"), "category": mode, "content": content})
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=4)
            st.success("✅ 發射成功")
        except Exception as e:
            st.error(f"❌ 發射失敗: {str(e)}")

st.subheader("📚 歷史經文典藏")
for item in load_history():
    with st.expander(f"📅 {item.get('date')} - {item.get('category')}"):
        st.markdown(item.get('content'))
