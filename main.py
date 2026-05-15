import streamlit as st
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage

# --- 安全讀取配置 ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    LINE_ACCESS_TOKEN = st.secrets["LINE_ACCESS_TOKEN"]
    LINE_USER_ID = st.secrets["LINE_USER_ID"]
except Exception:
    st.error("❌ Secrets 配置遺失，請至 Streamlit 後台設定。")
    st.stop()

# 初始化
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

st.title("🛡️ 聖經 AI 安全控制台")
st.write(f"歡迎回來，**Brett**。")

if st.button("🚀 執行：安全推送任務"):
    try:
        # --- 自動偵測可用模型邏輯 ---
        # 這裡會嘗試抓取您的 API Key 權限下所有可用模型
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 優先選擇 flash，若無則選第一個可用的
        target_model = 'gemini-1.5-flash'
        if f'models/{target_model}' not in available_models:
            target_model = available_models[0].split('/')[-1] if available_models else None
            
        if not target_model:
            st.error("❌ 您的 API Key 目前沒有可用的生成模型權限。")
            st.stop()

        model = genai.GenerativeModel(target_model)
        response = model.generate_content("請提供一段充滿力量的聖經經文與50字內的啟示。")
        
        if response.text:
            line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【安全任務】\n\n{response.text}"))
            st.success(f"任務成功！使用模型: {target_model}")
            st.balloons()
            
    except Exception as e:
        st.error(f"系統異常：{str(e)}")
        st.info("💡 如果還是 404，請確認 Python 版本是否已調回 3.11。")
