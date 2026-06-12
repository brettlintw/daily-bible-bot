import streamlit as st
import json
import os
from fpdf import FPDF

# --- 設定檔名 ---
DB_FILE = "bible_history.json"

st.set_page_config(page_title="靈修控制台", layout="wide")
st.title("靈修自動化控制台")

# --- 讀取函式 (防禦性修正) ---
def load_history():
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        st.error(f"歷史紀錄讀取失敗: {e}")
        return []

# --- 5. 歷史紀錄庫 (完整修復版) ---
st.subheader("📚 歷史經文典藏管理庫")
history_data = load_history()

if history_data:
    c1, c2, c3 = st.columns([1, 1, 1])
    
    # 匯出 TXT
    with c1:
        txt_data = "".join([f"{h['date']} {h['time']} | {h['category']}\n{h['content']}\n---\n" for h in history_data])
        st.download_button("📥 下載 TXT", txt_data, "history.txt")
        
    # 匯出 PDF (防禦性處理)
    with c2:
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=10)
            for h in history_data:
                # 將無法顯示的字元轉為 "?" 防止程式崩潰
                clean_content = h['content'].encode('latin-1', 'replace').decode('latin-1')
                pdf.cell(200, 10, txt=f"{h['date']} - {h['category']}", ln=True)
                pdf.multi_cell(0, 10, txt=clean_content)
                pdf.cell(200, 10, txt="--------------------------", ln=True)
            st.download_button("📥 下載 PDF", bytes(pdf.output(dest='S')), "history.pdf", "application/pdf")
        except Exception as e:
            st.warning("PDF 生成失敗，建議下載 TXT。")

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
