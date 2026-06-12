import os
import random
import json
import google.generativeai as genai
from linebot import LineBotApi
from linebot.models import TextSendMessage

# 1. 初始化 (保持不變)
genai.configure(api_key=os.environ['GEMINI_API_KEY'])
model = genai.GenerativeModel('gemini-2.5-flash')

# 2. 生成內容 (新增隨機化邏輯)
# 透過 random 產生一個不同的心情主題或經文類別，增加多樣性
themes = ["安慰", "力量", "盼望", "智慧", "愛與饒恕", "平安", "信心"]
chosen_theme = random.choice(themes)

prompt = f"""
請作為溫柔牧者，針對主題「{chosen_theme}」，精選一段聖經經文進行分享。
為了確保內容新鮮，請從聖經中挑選一段較少被提及但深具意義的經文。

格式嚴格要求：
【經文內容】
(經文內容，最後手動加上 (阿們。))
【經文章節】
(例如：(詩篇 4:8))
【領受與感悟】
(撰寫一段深度溫暖的靈修反思)

鐵律：禁止重複分享過去發送過的常見經文，內容禁止斷章，總字數 600 字內。
"""

# 使用 generation_config 增加 temperature 來提高隨機性 (創意度)
res = model.generate_content(
    prompt,
    generation_config=genai.types.GenerationConfig(temperature=0.8)
)
payload = res.text.strip()

# 3. 推送至 LINE (保持不變)
line_api = LineBotApi(os.environ['LINE_TOKEN'])
line_api.push_message('Uf166c741223bc8ee5d82fd1fd9f4df86', TextSendMessage(text=f'【每日靈修】\n\n{payload}'))
print('發送成功！')
