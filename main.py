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

# 頁面配置
st.set_page_config(page_title="靈修控制台", layout="wide")
st.title("🛡️ 聖經-LINE推送 V60.1 版 (雙模整合版)")

# --- 輔助函式 ---
def load_history():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return []
    return []

# --- 側邊欄：系統狀態 ---
st.sidebar.header("⚙️ 系統狀態")
st.sidebar.info("模式：雙模運作 (GitHub Actions 自動推播 + Render Webhook 互動)")

# --- 主畫面：推送控制台 ---
st.subheader("🚀 手動精準推送")
col1, col2 = st.columns([2, 1])

with col1:
    api_key = st.text_input("Gemini API Key", type="password", help="用於生成經文")
    line_token = st.text_input("LINE Channel Access Token", type="password")
    target_id = st.text_input("目標 UserID / 群組 ID", help="輸入個人 ID 或群組 ID")

with col2:
    theme = st.selectbox("選擇主題", ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"])
    if st.button("執行推送"):
        if not all([api_key, line_token, target_id]):
            st.error("請填寫完整資訊")
        else:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash')
                res = model.generate_content(f"請針對「{theme}」主題分享聖經經文。格式：【經文內容】；【章節】；【感悟】")
                
                line_api = LineBotApi(line_token)
                line_api.push_message(target_id, TextSendMessage(text=f'【靈修分享】\n\n{res.text.strip()}'))
                
                # 寫入歷史
                history = load_history()
                history.insert(0, {"date": datetime.now(TZ_TW).strftime("%Y-%m-%d"), "category": theme, "content": res.text.strip()})
                with open(DB_FILE, "w", encoding="utf-8") as f:
                    json.dump(history, f, ensure_ascii=False, indent=4)
                st.success("✅ 發射成功！")
            except Exception as e:
                st.error(f"❌ 發射失敗: {e}")

# --- 歷史紀錄 ---
st.divider()
st.subheader("📚 歷史經文典藏")
history_data = load_history()
if history_data:
    st.table(history_data[:10])  # 顯示最近 10 筆
    if st.download_button("下載完整紀錄 (JSON)", json.dumps(history_data, ensure_ascii=False, indent=4), "history.json"):
        st.success("下載完成")
