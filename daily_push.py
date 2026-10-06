import os
import time
import logging
from datetime import datetime, timedelta
import bible_core

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


PUSH_HOUR_TW = 12
MAX_WAIT_SECONDS = 45 * 60


def wait_until_push_time():
    """排程提早啟動，這裡等到台灣時間整點才推播；已過整點（Actions 遲到）就立刻推。手動觸發不等待。"""
    if os.environ.get('GITHUB_EVENT_NAME') != 'schedule':
        return
    now = datetime.now(bible_core.TZ_TW)
    target = now.replace(hour=PUSH_HOUR_TW, minute=0, second=0, microsecond=0)
    wait = (target - now).total_seconds()
    if 0 < wait <= MAX_WAIT_SECONDS:
        logger.info(f"提早啟動，等待 {int(wait)} 秒到 {target.strftime('%H:%M:%S')} 再推播")
        time.sleep(wait)


def main():
    target_id = os.environ.get('TARGET_GROUP_ID', '').strip()
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    line_token = os.environ.get('LINE_TOKEN', '').strip()
    admin_user_id = os.environ.get('ADMIN_USER_ID', '').strip()

    if not all([target_id, api_key, line_token]):
        return

    with open(bible_core.ID_FILE, "w") as f:
        f.write(target_id)

    try:
        payload, chosen_theme = bible_core.generate_verse(api_key)
        wait_until_push_time()
        bible_core.send_line_message(line_token, target_id, f'【每日靈修】\n\n{payload}')
        bible_core.record_entry(payload, f"自動靈修-{chosen_theme}")
    except Exception as e:
        logger.error(f"系統錯誤: {e}")
        if admin_user_id:
            try:
                bible_core.send_line_message(
                    line_token,
                    admin_user_id,
                    f'⚠️ 今日自動推播失敗\n所有 Gemini 模型都無法使用，請檢查額度/計費狀態。\n錯誤訊息：{e}'
                )
            except Exception as notify_error:
                logger.error(f"通知管理員失敗: {notify_error}")


if __name__ == "__main__":
    main()
