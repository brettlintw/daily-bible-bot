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
    st.error("❌ Secrets 配置遺失，請檢查 Streamlit 後台。")
    st.stop()

# 初始化
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)

st.title("🛡️ 聖經 AI 安全控制台")
st.write(f"歡迎回來，**Brett**。")

if st.button("🚀 執行：安全推送任務"):
    try:
        # 強制使用穩定版模型名稱
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content("請提供一段充滿力量的聖經經文與50字內的鼓勵。")
        
        # 確保有內容回傳
        if response.text:
            line_bot_api.push_message(LINE_USER_ID, TextSendMessage(text=f"【安全任務】\n\n{response.text}"))
            st.success("任務成功！新 API Key 已生效。")
            st.balloons()
    except Exception as e:
        # 如果新 Key 還是有問題，這裡會顯示原因
        st.error(f"系統異常：{str(e)}")
        if "404" in str(e):
            st.info("💡 提示：請確認您的新 API Key 在 AI Studio 中是否顯示為 Active 狀態。")
