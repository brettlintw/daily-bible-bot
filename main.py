import streamlit as st
import json
import os
import time
from datetime import datetime, timezone, timedelta
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage
from fpdf import FPDF

# --- 設定 ---
DB_FILE = "bible_history.json"
TZ_TW = timezone(timedelta(hours=8))

st.set_page_config(page_title="靈修控制台", layout="wide")
st.title("🛡️ 聖經-LINE推送 V60.0 版")

# --- 輔助函式 ---
def scan_secret_keys():
    return {f"🔑 金鑰 #{i}": st.secrets.get(f"GEMINI_API_KEY{'' if i==1 else '_'+str(i)}", "") for i in range(1, 6) if st.secrets.get(f"GEMINI_API_KEY{'' if i==1 else '_'+str(i)}")}

def discover_supported_models(target_key):
    if not target_key: return {"⚠️ 請先選擇金鑰": {"model_id": "gemini-2.5-flash"}}
    options = {"🚀 gemini-2.5-flash ── 【極速型】": {"model_id": "gemini-2.5-flash"}}
    try:
        genai.configure(api_key=target_key)
        for m in genai.list_models():
            if "gemini" in m.name:
                m_id = m.name.split('/')[-1]
                options[f"🚀 {m_id} ── 【可用模型】"] = {"model_id": m_id}
    except: pass
    return options

def load_history():
    if not os.path.exists(DB_FILE): return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except: return []

# --- UI 設定與模型選擇 ---
KEY_POOL = scan_secret_keys()
chosen_key = st.selectbox("🔑 金鑰：", options=list(KEY_POOL.keys()))
MODEL_REGISTRY = discover_supported_models(KEY_POOL[chosen_key])
chosen_model = st.selectbox("🚀 模型：", options=list(MODEL_REGISTRY.keys()))

# --- 推送邏輯 ---
mode = st.radio("維度：", ["全員廣播", "精準推送", "AI 智慧廣播"], horizontal=True)
with st.form("push_form"):
    uids = st.text_input("User ID (逗號分隔):") if mode == "精準推送" else ""
    mood = st.text_input("心情主題:") if mode == "AI 智慧廣播" else ""
    text = st.text_area("內文:") if mode != "AI 智慧廣播" else ""
    
    if st.form_submit_button("🚀 發射"):
        try:
            genai.configure(api_key=KEY_POOL[chosen_key])
            model = genai.GenerativeModel(MODEL_REGISTRY[chosen_model]["model_id"])
            
            if mode == "AI 智慧廣播":
                prompt = f"請針對主題「{mood}」，選取一段聖經經文分享。格式：【經文內容】(阿們。)；【經文章節】；【領受與感悟】。禁止贅字，內容完整禁止斷章。"
                content = model.generate_content(prompt).text
            else:
                content = text
            
            line_api = LineBotApi(st.secrets.get("LINE_ACCESS_TOKEN", ""))
            if mode == "全員廣播":
                line_api.broadcast(TextSendMessage(text=content))
            else:
                line_api.push_message(uids, TextSendMessage(text=content))
            
            # 存入歷史
            history = load_history()
            history.insert(0, {"date": datetime.now(TZ_TW).strftime("%Y-%m-%d"), "time": datetime.now(TZ_TW).strftime("%H:%M:%S"), "category": mode, "content": content})
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=4)
            st.success("✅ 發射成功")
        except Exception as e:
            st.error(f"❌ 發射失敗: {str(e)}")

# --- 5. 歷史紀錄庫 (防禦性匯出 - 穩定版) ---
st.subheader("📚 歷史經文典藏管理庫")
history_data = load_history()

if history_data:
    c1, c2, c3 = st.columns([1, 1, 1])
    
    # 匯出 TXT
    with c1:
        txt_data = "".join([f"{h['date']} {h['time']} | {h['category']}\n{h['content']}\n---\n" for h in history_data])
        st.download_button("📥 下載 TXT", txt_data, "history.txt")
        
    # 匯出 PDF (絕對穩定版：跳過外部字體依賴)
    with c2:
        try:
            # 建立 PDF 物件，強制使用 Courier (PDF 標準內建字體，無需系統路徑)
            pdf = FPDF(orientation='P', unit='mm', format='A4')
            pdf.add_page()
            pdf.set_font("Courier", size=10)
            
            for h in history_data:
                # 使用編碼替換處理：將所有不支援的中文字元轉為 "?"
                # 這能保證 PDF 一定會生成，不會再報 Font not found 或 encoding error
                clean_content = h['content'].encode('latin-1', 'replace').decode('latin-1')
                pdf.cell(0, 10, txt=f"{h['date']} - {h['category']}", ln=True)
                pdf.multi_cell(0, 10, txt=clean_content)
                pdf.cell(0, 10, txt="--------------------------", ln=True)
            
            st.download_button("📥 下載 PDF (穩定版)", bytes(pdf.output(dest='S')), "history.pdf", "application/pdf")
        except Exception as e:
            st.error(f"PDF 生成器初始化失敗: {e}")
            st.info("建議改用 TXT 匯出，相容性最高。")

    # 清除記錄
    with c3:
        if st.button("⚠️ 清除所有記錄"):
            if os.path.exists(DB_FILE):
                os.remove(DB_FILE)
            st.rerun()

    # 顯示歷史清單
    for item in reversed(history_data):
        with st.expander(f"📅 {item['date']} ⏰ {item['time']} - {item['category']}"):
            st.markdown(item['content'])
else:
    st.info("目前尚無歷史經文紀錄，等待自動排程執行中...")
