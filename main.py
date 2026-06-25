import streamlit as st
import json
import os
import random
import google.generativeai as genai
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, TextMessage
from datetime import datetime, timezone, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential
from itertools import groupby

# --- 1. 設定區 ---
DB_FILE = "bible_history.json"
ID_FILE = "latest_group_id.txt"
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

# --- [v3] 封裝推送函式 ---
def send_line_message(target_id, message_text):
    configuration = Configuration(access_token=get_secret("LINE_TOKEN"))
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.push_message(
            PushMessageRequest(
                to=target_id,
                messages=[TextMessage(text=message_text)]
            )
        )

# --- 2. 系統自動配置 ---
st.sidebar.header("⚙️ 系統鎖定配置")
# (略過與原版相同的偵測與設定區...)
st.sidebar.subheader("🔍 群組 ID 比對偵測器")
if os.path.exists(ID_FILE):
    with open(ID_FILE, "r") as f:
        detected_id = f.read().strip()
        st.sidebar.info(f"偵測到的群組 ID:\n{detected_id}")
line_token = st.sidebar.text_input("LINE Token:", value=get_secret("LINE_TOKEN"), type="password")
model_name = get_secret("GEMINI_MODEL_NAME") or "models/gemini-flash-latest"
st.sidebar.info(f"當前 AI 模型: {model_name}")

# --- 3. 靈修推送核心邏輯 ---
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def generate_with_retry(model, prompt):
    return model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.8))

st.subheader("🚀 手動精準推送")
target_id = st.text_input("目標 UserID / 群組 ID", value=DEFAULT_TARGET_ID)

if st.button("執行推送"):
    # (此區邏輯保持不變...)
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
            send_line_message(target_id.strip(), f'【每日靈修】\n\n{payload}')
            st.success(f"✅ 發送成功 (主題: {chosen_theme})")
            history = load_history()
            history.insert(0, {"date": datetime.now(TZ_TW).strftime("%Y-%m-%d"), "time": datetime.now(TZ_TW).strftime("%H:%M:%S"), "category": f"手動-{chosen_theme}", "content": payload})
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"❌ 系統故障: {str(e)}")

# --- 4. 歷史管理 (優化版：以年月分頁 + 縮放控制) ---
st.subheader("📚 歷史經文典藏管理庫")
history_data = load_history()

if history_data:
    # 提取年月鍵值並分組
    for entry in history_data:
        date_obj = datetime.strptime(entry.get("date", "2000-01-01"), "%Y-%m-%d")
        entry["year_month"] = date_obj.strftime("%Y年%m月")

    grouped_history = {k: list(v) for k, v in groupby(history_data, key=lambda x: x["year_month"])}
    months = list(grouped_history.keys())
    
    # 全部展開/收合的控制開關
    if st.checkbox("預設全部展開 (取消勾選則全部收合)", value=False):
        expand_all = True
    else:
        expand_all = False

    tabs = st.tabs(months)
    for i, month in enumerate(months):
        with tabs[i]:
            for h in grouped_history[month]:
                # 使用 expanded 參數控制預設縮放狀態
                with st.expander(f"📅 {h.get('date', '無日期')} {h.get('time', '')} | {h.get('category', '無分類')}", expanded=expand_all):
                    st.markdown(h.get('content', '無內容'))
