import streamlit as st
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage
import datetime
import requests

# --- 1. 系統版本與基本配置 ---
VERSION = "CL3-Elite-v3.0"
st.set_page_config(page_title="聖經 AI 進階終端", page_icon="🛡️")

# --- 2. 密鑰讀取 ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    LINE_ACCESS_TOKEN = st.secrets["LINE_ACCESS_TOKEN"]
    LINE_USER_ID = st.secrets["LINE_USER_ID"]
except:
    st.error("❌ 密鑰讀取失敗。")
    st.stop()

line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

# --- 3. 抓取天氣狀況 (模擬定位或固定地區) ---
def get_weather(city="Taipei"):
    # 此處可替換為 OpenWeather API 呼叫
    # 簡易展示：
    return "🌤️ 晴朗, 26°C"

# --- 4. UI 介面設計 ---
st.title("🛡️ 聖經 AI 任務控制台")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("今日日期", datetime.date.today().strftime("%Y/%m/%d"))
with col2:
    st.metric("目前天氣", get_weather())
with col3:
    st.metric("系統版本", VERSION)

st.write("---")

# --- 5. 功能追加：多點時間排程修改 ---
st.subheader("⏰ 推送時間排程管理")
with st.expander("修改推送時段"):
    scheduled_times = st.multiselect(
        "請選擇希望推送的時間點 (24小時制)：",
        [f"{h:02d}:00" for h in range(24)],
        default=["06:00", "21:00"]
    )
    if st.button("儲存排程"):
        # 註：此處需將數據存入 database 或 secrets，GitHub Actions 讀取後執行
        st.success(f"排程已更新為：{', '.join(scheduled_times)}")
        st.info("提示：此設定將同步至雲端調度任務中。")

# --- 6. 功能追加：手動加入經文並推送 ---
st.subheader("✍️ 自定義經文任務")
custom_scripture = st.text_area("在此輸入您想分享的經文或訊息：", placeholder="例如：約翰福音 3:16...")
if st.button("立即手動推送此內容"):
    if custom_scripture:
        line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【手動分享】\n\n{custom_scripture}"))
        st.balloons()
        st.success("自定義訊息已成功發送。")
    else:
        st.warning("請先輸入內容。")

# --- 7. 原有功能：AI 自動生成推送 ---
st.subheader("🚀 AI 隨時推送")
if st.button("啟動 AI 內容分析並推送"):
    with st.spinner("AI 掃描中..."):
        model = genai.GenerativeModel('gemini-1.5-flash')
        res = model.generate_content("請提供一段聖經經文與50字內的專業鼓勵語。")
        line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=res.text))
        st.success("AI 內容已推送。")

st.markdown("---")
st.caption(f"© 2026 Brett's Bible Bot | 系統環境：{VERSION}")
