import streamlit as st
import google.generativeai as genai
from datetime import datetime, timedelta, timezone
import random
import time
import threading
import json
import os

# --- 1. 頁面配置 (旗艦一頁式) ---
st.set_page_config(page_title="聖經控制台 V16.0", page_icon="🛡️", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .main .block-container { max-width: 80% !important; padding: 0.3rem 1rem !important; }
    @media (max-width: 1023px) { .main .block-container { max-width: 100% !important; padding: 0.3rem !important; } }
    h1 { font-size: 1.15rem !important; margin: 0 !important; line-height: 1.1 !important; color: #E0E0E0; }
    .stTextArea>div>div>textarea { height: 55px !important; border-radius: 8px; }
    .stTextInput>div>div>input { height: 2.1rem !important; border-radius: 8px; }
    .stButton>button { border-radius: 8px; height: 2.5rem; font-weight: bold; }
    .log-box { font-size: 0.65rem; background: #121212; color: #00FF41; padding: 6px; border-radius: 8px; font-family: monospace; height: 65px; overflow-y: auto; border: 1px solid #333; }
    .status-tag { font-size: 0.7rem; padding: 2px 8px; border-radius: 10px; background: #2E7D32; color: white; margin-left: 10px; }
    .history-card { background: #1E1E1E; padding: 10px; border-radius: 8px; border-left: 5px solid #0288D1; margin-bottom: 8px; color: #E0E0E0; }
    .type-tag-auto { background: #2E7D32; color: white; padding: 1px 6px; border-radius: 4px; font-size: 0.65rem; }
    .type-tag-manual { background: #C62828; color: white; padding: 1px 6px; border-radius: 4px; font-size: 0.65rem; }
    .type-tag-ai { background: #1565C0; color: white; padding: 1px 6px; border-radius: 4px; font-size: 0.65rem; }
    [data-testid="stHeader"], footer, #MainMenu { visibility: hidden; height: 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心配置 ---
def get_cfg(key, fallback):
    try: return st.secrets.get(key, fallback) or fallback
    except: return fallback

GEMINI_API_KEY = get_cfg("GEMINI_API_KEY", "")
LINE_TOKEN = get_cfg("LINE_ACCESS_TOKEN", "")
TRIGGER_KEY = get_cfg("TRIGGER_KEY", "KITT_SECURE_KEY_2026") # 安全安全密鑰，防止外人亂戳網址
TZ_TW = timezone(timedelta(hours=8))

from linebot import LineBotApi
from linebot.models import TextSendMessage
line_api = LineBotApi(LINE_TOKEN)

genai.configure(api_key=GEMINI_API_KEY)
DB_FILE = "bible_history.json"

# --- 3. 典藏庫資料核心控制 ---
def save_to_history(category, content):
    now_tw = datetime.now(TZ_TW)
    date_str = now_tw.strftime("%Y-%m-%d")
    time_str = now_tw.strftime("%H:%M:%S")
    
    new_entry = {
        "id": int(time.time() * 1000),
        "date": date_str,
        "time": time_str,
        "category": category,
        "content": content
    }
    
    lock = threading.Lock()
    with lock:
        data = []
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f: data = json.load(f)
            except: data = []
        data.insert(0, new_entry)
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

# --- 4. 經文發射核心邏輯 (內建斷字智慧偵測盾) ---
def execute_ai_bible_generation(source_label="自動排程"):
    model = genai.GenerativeModel(model_name="gemini-2.5-flash")
    
    prompt = (
        "你是溫柔牧者，請精選一段聖經經文，並給予深度的反思與領受。\n\n"
        "【輸出嚴格格式要求】：\n"
        "1. 第一行必須明確寫出【經文章節】，例如：(約翰福音 3:16) 或 (詩篇 23:1)\n"
        "2. 第二行寫出完整的【經文內容】\n"
        "3. 第三行寫出【今日反思與領受】，字數控制在200-300字內，精煉且深刻。\n"
        "4. 直接輸出純文字，不要使用任何 ** 粗體符號或 # 標題符號。\n"
        "5. 【關鍵安全防線】：全文必須字句完整，最後一個字必須在一個完整的「句號」或「右括號」處優雅結束，絕對不可在句子中途斷掉。"
    )
    
    # 進行最多 3 次重新點火嘗試，防止斷句幽靈
    for attempt in range(3):
        res = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.70, top_p=0.85, max_output_tokens=1000
            )
        )
        if res and res.text:
            text = str(res.text).strip()
            # 偵測結尾是否合法（防止斷字）
            if text.endswith('。') or text.endswith('」') or text.endswith(')') or text.endswith('）'):
                return text
            else:
                time.sleep(1) # 稍微冷卻，重新向衛星要一次
    
    # 如果真的不幸3次都斷掉，做保底強制修正補上句號
    return str(res.text).strip() + " (阿們。)"

# --- 5. 網頁外部鉤子接收器 (解決九點定時失敗) ---
# 透過 Streamlit 的網頁 URL 參數機制，讓 GitHub Actions 從外部一鍵點火
query_params = st.query_params
if "action" in query_params and "key" in query_params:
    if query_params["action"] == "trigger_push" and query_params["key"] == TRIGGER_KEY:
        # 執行鋼鐵時間鎖，防止 GitHub 多次重複戳
        date_today = datetime.now(TZ_TW).strftime("%Y-%m-%d")
        
        # 讀取今天是否發過
        history_data = []
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f: history_data = json.load(f)
            except: pass
        
        already_pushed = any(h['date'] == date_today and h['category'] == "定時推送" for h in history_data)
        
        if not already_pushed:
            safe_text = execute_ai_bible_generation(source_label="自動排程")
            line_api.broadcast(TextSendMessage(text=f"【自動排程推送】\n\n{safe_text}"))
            save_to_history("定時推送", safe_text)
            st.success("🛰️ GitHub 外部鉤子點火成功，經文已完美發射！")
        else:
            st.warning("🛡️ 時間鎖防禦：今日定時推送已存在，拒絕重複發射。")
        st.stop()

# --- 6. UI 佈局 ---
st.markdown(f"<h1>🛡️ 聖經任務控制台 V16.0 <span class='status-tag'>🛰️ 斷字修復盾就位</span></h1>", unsafe_allow_html=True)
st.caption(f"📅 {datetime.now(TZ_TW).strftime('%Y/%m/%d')} | 🚀 外部 GitHub 聯航對接版")

# ⏰ 排程管理（提示改為外部接管）
with st.expander("⏰ 排程航線狀態", expanded=False):
    st.info("💡 系統已升級至 V16.0！內部計時 Thread 已由更穩固的 GitHub Actions 外部排程器接管，免除 Uptime 第三方軟體冬眠魔咒。")
    st.code(f"網頁點火專屬 URL 鉤子：\nhttps://YOUR_APP_URL/?action=trigger_push&key={TRIGGER_KEY}")

# ✍️ 手動廣播
st.subheader("✍️ 手動全員廣播")
with st.form("manual_form", clear_on_submit=False):
    custom_text = st.text_area("內容：", placeholder="在此輸入要廣播給所有好友的文字...", label_visibility="collapsed")
    if st.form_submit_button("📢 執行全員廣播"):
        if custom_text.strip():
            try:
                line_api.broadcast(TextSendMessage(text=f"【手動推送】\n\n{custom_text}"))
                save_to_history("手動廣播", custom_text)
                st.toast("✅ 已送達並完成歸檔")
            except Exception as line_err:
                st.error(f"連線異常: {str(line_err)[:20]}")

st.markdown("---")

# 🤖 AI 智慧廣播
st.subheader("🤖 AI 智慧廣播")
c1, c2, c3 = st.columns([1, 1, 1])
with c1: mood_input = st.text_input("心情：", placeholder="心情...", label_visibility="collapsed")
with c2: persona = st.selectbox("風格：", ["暖心", "專業", "KITT"], label_visibility="collapsed")
with c3: content_type = st.selectbox("內容：", ["聖經經文", "推薦詩歌"], label_visibility="collapsed")

if st.button("✨ 啟動 AI 廣播"):
    try:
        if content_type == "聖經經文":
            with st.spinner("✨ 斷字防禦盾正在校準經文字句完整度..."):
                safe_text_manual = execute_ai_bible_generation(source_label="AI智慧廣播")
            header = "【AI經文推送】"
            line_api.broadcast(TextSendMessage(text=f"{header}\n\n{safe_text_manual}"))
            save_to_history("AI智慧廣播", f"{header}\n{safe_text_manual}")
            st.toast("✨ 廣播並完成歸檔")
        else:
            model = genai.GenerativeModel(model_name="gemini-2.5-flash")
            persona_map = {"暖心": "溫柔牧者。", "專業": "分析師。", "KITT": "KITT，稱呼Brett。"}
            prompt = (
                f"{persona_map[persona]} 針對用戶『{mood_input if mood_input else '疲累'}』的心情推薦基督教詩歌(含歌名歌詞)。\n"
                f"結構必須絕對完整結尾，直接輸出純文字，不要使用粗體或標題符號。"
            )
            res = model.generate_content(prompt)
            if res and res.text:
                safe_text_song = str(res.text).strip()
                header = "【AI詩歌推薦】"
                line_api.broadcast(TextSendMessage(text=f"{header}\n\n{safe_text_song}"))
                save_to_history("AI智慧廣播", f"{header}\n{safe_text_song}")
                st.toast("✨ 詩歌廣播完成")
    except Exception as e:
        st.error(f"對接失敗: {str(e)[:40]}")

st.markdown("---")

# 歷史經文管理艙
st.subheader("📚 歷史經文典藏管理庫")
history_data = []
if os.path.exists(DB_FILE):
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f: history_data = json.load(f)
    except: history_data = []

if history_data:
    download_lines = [f"========================================\n日期時間: {h['date']} {h['time']}\n分類標籤: {h['category']}\n----------------------------------------\n{h['content']}\n========================================\n\n" for h in history_data]
    st.download_button(label="📥 下載完整歷史經文到本地電腦 (.txt)", data="".join(download_lines), file_name=f"bible_history_{datetime.now(TZ_TW).strftime('%Y%m%d')}.txt", mime="text/plain")
    
    filter_type = st.selectbox("🔍 按推送類型過濾顯示：", ["全部", "定時推送", "手動廣播", "AI智慧廣播"])
    for item in history_data:
        if filter_type != "全部" and item['category'] != filter_type: continue
        tag_class = "type-tag-auto" if item['category'] == "定時推送" else ("type-tag-manual" if item['category'] == "手動廣播" else "type-tag-ai")
        st.markdown(f'<div class="history-card"><strong>📅 {item["date"]} &nbsp;&nbsp; ⏰ {item["time"]}</strong> &nbsp;&nbsp; <span class="{tag_class}">{item["category"]}</span><pre style="white-space: pre-wrap; font-family: sans-serif; background: transparent; border: none; padding: 0; margin-top: 8px; color: #B0BEC5; font-size: 0.8rem;">{item["content"]}</pre></div>', unsafe_allow_html=True)
else:
    st.info("💡 儲存艙目前尚無歷史保存紀錄。")
