import streamlit as st
import json
import os
from datetime import datetime, timezone, timedelta
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 1. 極速優先觸發器 (手動測試按鈕) ---
def trigger_test_push():
    """
    僅用於 Streamlit 網頁 UI 的手動測試按鈕。
    核心自動化邏輯已完全轉移至 GitHub Actions。
    """
    from linebot import LineBotApi
    from linebot.models import TextSendMessage
    import time
    
    try:
        # 使用儲存於 Secrets 的 Token (UI 測試用)
        token = st.secrets.get("LINE_ACCESS_TOKEN", "")
        my_user_id = 'Uf166c741223bc8ee5d82fd1fd9f4df86'
        
        line_api = LineBotApi(token)
        line_api.push_message(my_user_id, TextSendMessage(text="【UI測試】系統運作正常，手動發送成功！"))
        
        time.sleep(1) # 短暫延遲確保 UI 回應
        return "TEST_PUSH_DONE"
        
    except Exception as e:
        error_msg = f"TEST_ERROR: {str(e)}"
        print(error_msg) 
        return error_msg

# 優先攔截器
params = st.query_params
if params.get("action") == "fixed_push" and params.get("key") == "KITT_SECURE_KEY_2026":
    st.write(execute_fixed_push_logic())
    st.stop()

# --- 2. 主程式設定 ---
SYSTEM_VERSION = "V60.0 版"
TZ_TW = timezone(timedelta(hours=8))
DB_FILE = "bible_history.json"

# --- 3. 輔助函數 ---
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

def save_to_history(category, content):
    data = []
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except: pass
    data.insert(0, {"date": datetime.now(TZ_TW).strftime("%Y-%m-%d"), "time": datetime.now(TZ_TW).strftime("%H:%M:%S"), "category": category, "content": content})
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 4. UI 介面 ---
st.set_page_config(page_title="聖經控制台", layout="centered")
st.title(f"🛡️ 聖經-LINE推送 {SYSTEM_VERSION}")

KEY_POOL = scan_secret_keys()
chosen_key = st.selectbox("🔑 金鑰：", options=list(KEY_POOL.keys()))
MODEL_REGISTRY = discover_supported_models(KEY_POOL[chosen_key])
chosen_model = st.selectbox("🚀 模型：", options=list(MODEL_REGISTRY.keys()))

mode = st.radio("維度：", ["全員廣播", "精準推送", "AI 智慧廣播"], horizontal=True)
with st.form("manual_push"):
    uids = st.text_input("User ID (逗號分隔):") if mode == "精準推送" else ""
    mood = st.text_input("心情主題:") if mode == "AI 智慧廣播" else ""
    text = st.text_area("內文:") if mode != "AI 智慧廣播" else ""
    
    if st.form_submit_button("🚀 發射"):
        try:
            genai.configure(api_key=KEY_POOL[chosen_key])
            model = genai.GenerativeModel(MODEL_REGISTRY[chosen_model]["model_id"])
            
# 修正後的 AI 智慧廣播邏輯
            if mode == "AI 智慧廣播":
                # 修改提示詞，強制要求 AI 僅針對一個心情主題生成一段內容
                prompt = f"""
                請作為溫柔的牧者，針對心情主題：'{mood}'，選取一段最合適的聖經經文進行分享。
                
        你是溫柔牧者。請精選一段聖經經文進行分享，嚴格遵守以下格式：
        【經文內容】
        (經文內容，最後手動加上 (阿們。))
        【經文章節】
        (例如：(詩篇 4:8))
        【領受與感悟】
        (撰寫一段深度溫暖的靈修反思)
        鐵律：禁止任何前言、贅字，總字數 600 字內，內容完整禁止斷章。
                """
                res = model.generate_content(prompt)
                content = res.text
            else:
                content = text
            
            line_api = LineBotApi(st.secrets.get("LINE_ACCESS_TOKEN", ""))
            line_api.broadcast(TextSendMessage(text=content))
            
            save_to_history(mode, content)
            st.success("✅ 發射成功")
        except Exception as e:
            st.error(f"❌ 發射失敗: {str(e)}")

# --- 5. 歷史紀錄庫 (PDF 防禦性匯出 - 修正縮排版) ---
if history_data:
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1: 
        txt_data = "".join([f"{h['date']} {h['time']} | {h['category']}\n{h['content']}\n---\n" for h in history_data])
        st.download_button("📥 下載 TXT", txt_data, "history.txt")
        
    with c2:
        try:
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=10)
            for h in history_data:
                # 解決中文字 PDF 崩潰的權宜之計：將中文字替換為 "?"
                clean_content = h['content'].encode('latin-1', 'replace').decode('latin-1')
                pdf.cell(200, 10, txt=f"{h['date']} - {h['category']}", ln=True)
                pdf.multi_cell(0, 10, txt=clean_content)
                pdf.cell(200, 10, txt="---", ln=True)
            
            st.download_button("📥 下載 PDF", bytes(pdf.output(dest='S')), "history.pdf", "application/pdf")
        except Exception as e:
            st.warning(f"PDF 生成器異常: {e}")

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
    st.info("目前尚無歷史經文紀錄。")
