import streamlit as st
import os
import bible_core
from datetime import datetime
from itertools import groupby

# --- 1. 設定區 ---
DEFAULT_TARGET_ID = "C8a7777fb460a7ca0479b1b33c82f7a16"

st.set_page_config(page_title="靈修控制台", layout="wide")
st.title("🛡️ 聖經-LINE推送 V60.5 正式版")

# --- 輔助函式 ---
def get_secret(key_name):
    return st.secrets.get(key_name, os.environ.get(key_name, ""))

# --- 2. 系統自動配置 ---
st.sidebar.header("⚙️ 系統鎖定配置")
st.sidebar.subheader("🔍 群組 ID 比對偵測器")
if os.path.exists(bible_core.ID_FILE):
    with open(bible_core.ID_FILE, "r") as f:
        detected_id = f.read().strip()
        st.sidebar.info(f"偵測到的群組 ID:\n{detected_id}")
line_token = st.sidebar.text_input("LINE Token:", value=get_secret("LINE_TOKEN"), type="password")
MODEL_OPTIONS = {"自動（依序嘗試，成本由低到高，推薦）": None}
MODEL_OPTIONS.update({f"{name}（{label}）": name for name, label in bible_core.FREE_MODEL_CANDIDATES})

st.subheader("🚀 手動精準推送")
target_id = st.text_input("目標 UserID / 群組 ID", value=DEFAULT_TARGET_ID)
selected_label = st.selectbox("選擇生成模型：", list(MODEL_OPTIONS.keys()))
selected_model_name = MODEL_OPTIONS[selected_label]

if st.button("執行推送"):
    try:
        api_key = get_secret("GEMINI_API_KEY")
        line_token = get_secret("LINE_TOKEN")
        with st.spinner("🚀 牧者正在領受啟示..."):
            payload, chosen_theme = bible_core.generate_verse(api_key, selected_model_name)
        bible_core.send_line_message(line_token, target_id.strip(), f'【每日靈修】\n\n{payload}')
        bible_core.record_entry(payload, f"手動-{chosen_theme}")
        st.success(f"✅ 發送成功")
    except Exception as e:
        st.error(f"❌ 系統故障: {str(e)}")

# --- 4. 歷史管理 ---
st.subheader("📚 歷史經文典藏管理庫")
history_data = bible_core.load_history()

if history_data:
    # 預處理分組
    for entry in history_data:
        date_obj = datetime.strptime(entry.get("date", "2000-01-01"), "%Y-%m-%d")
        entry["year_month"] = date_obj.strftime("%Y年%m月")
    
    grouped_history = {k: list(v) for k, v in groupby(history_data, key=lambda x: x["year_month"])}
    months = list(grouped_history.keys())

    # 下載區塊優化：加入月份篩選
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button("📥 下載全部 (TXT)", data="\n\n".join([f"{h.get('date')} | {h.get('category')}\n{h.get('content')}" for h in history_data]), file_name="history_all.txt")
    with col2:
        selected_month = st.selectbox("選擇下載月份", months)
        monthly_data = grouped_history[selected_month]
        st.download_button(f"📄 下載 {selected_month} (HTML)", data=bible_core.generate_html_backup(monthly_data), file_name=f"history_{selected_month}.html", mime="text/html")
    with col3:
        st.download_button("📄 下載全部 (HTML)", data=bible_core.generate_html_backup(history_data), file_name="history_all.html", mime="text/html")
    
    # 顯示區塊
    expand_all = st.checkbox("預設全部展開", value=False)
    tabs = st.tabs(months)
    for i, month in enumerate(months):
        with tabs[i]:
            for h in grouped_history[month]:
                with st.expander(f"📅 {h.get('date', '無日期')} {h.get('time', '')} | {h.get('category', '無分類')}", expanded=expand_all):
                    st.markdown(h.get('content', '無內容'))
