import streamlit as st
import json
import os
import random
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage
from datetime import datetime, timezone, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential

# --- 1. 設定區 (Token 已硬編碼) ---
DB_FILE = "bible_history.json"
TZ_TW = timezone(timedelta(hours=8))
DEFAULT_TARGET_ID = "C43e597148c27a296e67e91d848773957"
FIXED_LINE_TOKEN = "vbmdbVqLgc0mlngXz67zuQun7awHSRdPhoqLookibRQQU7jBi8D+bC32nAIBHZfU8S1oy2XCA7Tr6F2pX4tb3JnExgTaoaxhthf7UNyiXNfiFwcpzuvEp4ghMgBbewf39cQE6p9bk02J5Lj2wsKJ0AdB04t89/1O/w1cDnyilFU="

st.set_page_config(page_title="靈修控制台", layout="wide")
st.title("🛡️ 聖經-LINE推送 V60.5 牧者靈修版")

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
line_token = st.sidebar.text_input("LINE Token (已自動載入):", value=FIXED_LINE_TOKEN, type="password")
st.sidebar.success("✅ LINE Token 已鎖定")

api_key_options = {f"🔑 金鑰 #{i}": get_secret(f"GEMINI_API_KEY{'' if i==1 else '_'+str(i)}") 
                   for i in range(1, 6) if get_secret(f"GEMINI_API_KEY{'' if i==1 else '_'+str(i)}")}

if not api_key_options:
    st.sidebar.error("⚠️ 未偵測到 GEMINI_API_KEY")
    api_key, selected_model = "", "gemini-2.5-flash"
else:
    selected_key_name = st.sidebar.selectbox("選擇 API 金鑰", list(api_key_options.keys()))
    api_key = api_key_options[selected_key_name]
    try:
        genai.configure(api_key=api_key)
        models = [m.name for m in genai.list_models() if "gemini" in m.name]
        selected_model = st.sidebar.selectbox("選擇 AI 模型", models)
    except: selected_model = "gemini-2.5-flash"

# --- 3. 靈修推送核心邏輯 ---
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def generate_with_retry(model, prompt):
    # 使用溫度 0.8 以保持牧者口吻的溫暖與靈動
    return model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.8))

st.subheader("🚀 手動精準推送")
target_id = st.text_input("目標 UserID / 群組 ID", value=DEFAULT_TARGET_ID)

if st.button("執行推送"):
    if not target_id.strip():
        st.error("❌ 目標 ID 不可為空！")
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(selected_model)
            
            # --- [牧者靈修 Prompt 邏輯] ---
            themes = ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"]
            chosen_theme = random.choice(themes)
            prompt = f"你是溫柔牧者。請針對主題「{chosen_theme}」，精選一段聖經經文。格式：【經文內容】(阿們。)；【章節】；【領受與感悟】。"
            
            with st.spinner(f"🚀 牧者正在領受「{chosen_theme}」主題的啟示..."):
                res = generate_with_retry(model, prompt)
            
            if res and res.text and len(res.text.strip()) > 0:
                payload = res.text.strip()
                # 強制截斷以符合 LINE 規範
                content_to_send = payload[:1950] + "\n...(內容過長已截斷)" if len(payload) > 2000 else payload
                
                line_api = LineBotApi(line_token.strip())
                line_api.push_message(target_id.strip(), TextSendMessage(text=f'【靈修分享】\n\n{content_to_send}'))
                st.success(f"✅ 發送成功 (主題: {chosen_theme})")
                
                # 紀錄歷史
                history = load_history()
                history.insert(0, {"date": datetime.now(TZ_TW).strftime("%Y-%m-%d"), "time": datetime.now(TZ_TW).strftime("%H:%M:%S"), "category": f"手動-{chosen_theme}", "content": content_to_send})
                with open(DB_FILE, "w", encoding="utf-8") as f:
                    json.dump(history, f, ensure_ascii=False, indent=4)
            else:
                st.error("❌ AI 未產出內容，請確認 API 配額！")
                        
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
