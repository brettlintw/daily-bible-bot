import os
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage

# 1. 初始化
genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash')

# 2. 生成內容
prompt = """
你是溫柔牧者。請精選一段聖經經文進行分享，嚴格遵守以下格式：
【經文內容】(阿們。)
【經文章節】
【領受與感悟】
鐵律：禁止任何前言、贅字，總字數 600 字內，內容完整禁止斷章。
"""
res = model.generate_content(prompt)
payload = res.text.strip()

# 3. 推送至 LINE
line_api = LineBotApi(os.environ['LINE_TOKEN'])
line_api.push_message('Uf166c741223bc8ee5d82fd1fd9f4df86', TextSendMessage(text=f'【每日靈修】\n\n{payload}'))
print('發送成功！')
