import streamlit as st
import json
import os
import random
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage
from datetime import datetime, timezone, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential

# --- 1. 設定區 ---
DB_FILE = "bible_history.json"
TZ_TW = timezone(timedelta(hours=8))
DEFAULT_TARGET_ID = "C8a7777fb460a7ca0479b1b33c82f7a16"

st.set_page_config(page_title="靈修控制台", layout="wide")
st.title("🛡️ 聖經-LINE推送 V60.5 正式版")

# --- 輔助函式 ---
def load_history():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return []
    return []

def get_secret(key_name):
    return st.secrets.get(key_name, os.environ.get(key_name, ""))

# --- 2. 系統自動配置 ---
st.sidebar.header("⚙️ 系統鎖定配置")
line_token = st.sidebar.text_input("LINE Token:", value=get_secret("LINE_TOKEN"), type="password")
st.sidebar.success("✅ LINE Token 已載入")

# 從環境變數獲取模型，若無則預設
model_name = get_secret("GEMINI_MODEL_NAME") or "models/gemini-flash-latest"
st.sidebar.info(f"當前 AI 模型: {model_name}")

# --- 3. 靈修推送核心邏輯 ---
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def generate_with_retry(model, prompt):
    return model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.8))

st.subheader("🚀 手動精準推送")
target_id = st.text_input("目標 UserID / 群組 ID", value=DEFAULT_TARGET_ID)

if st.button("執行推送"):
    if not target_id.strip():
        st.error("❌ 目標 ID 不可為空！")
    else:
        try:
            api_key = get_secret("GEMINI_API_KEY")
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            
            themes = ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"]
            chosen_theme = random.choice(themes)
            prompt = f"你是溫柔牧者。請針對主題「{chosen_theme}」，精選一段聖經經文。格式：【經文內容】(阿們。)；【章節】；【領受與感悟】。"
            
            with st.spinner(f"🚀 牧者正在領受「{chosen_theme}」主題的啟示..."):
                res = generate_with_retry(model, prompt)
            
            if res and res.text:
                payload = res.text.strip()
                line_api = LineBotApi(line_token.strip())
                line_api.push_message(target_id.strip(), TextSendMessage(text=f'【每日靈修】\n\n{payload}'))
                st.success(f"✅ 發送成功 (主題: {chosen_theme})")
                
                # 紀錄歷史
                history = load_history()
                history.insert(0, {"date": datetime.now(TZ_TW).strftime("%Y-%m-%d"), "time": datetime.now(TZ_TW).strftime("%H:%M:%S"), "category": f"手動-{chosen_theme}", "content": payload})
                with open(DB_FILE, "w", encoding="utf-8") as f:
                    json.dump(history, f, ensure_ascii=False, indent=4)
            else:
                st.error("❌ AI 未產出內容！")
        except Exception as e:
            st.error(f"❌ 系統故障: {str(e)}")

# --- 4. 歷史管理 ---
st.subheader("📚 歷史經文典藏管理庫")
history_data = load_history()
if history_data:
    st.download_button("📥 下載 TXT", "\n\n".join([f"{h.get('date', '無日期')} | {h.get('category', '無分類')}\n{h.get('content', '無內容')}" for h in history_data]), file_name="bible_history.txt")
    for h in history_data:
        with st.expander(f"📅 {h.get('date', '無日期')} {h.get('time', '')} | {h.get('category', '無分類')}"):
            st.markdown(h.get('content', '無內容'))
