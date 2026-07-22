import os
import logging
import bible_core

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    target_id = os.environ.get('TARGET_GROUP_ID', '').strip()
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    line_token = os.environ.get('LINE_TOKEN', '').strip()
    model_name = os.environ.get('GEMINI_MODEL_NAME', 'models/gemini-flash-latest')

    if not all([target_id, api_key, line_token]):
        return

    with open(bible_core.ID_FILE, "w") as f:
        f.write(target_id)

    try:
        payload, chosen_theme = bible_core.generate_verse(api_key, model_name)
        bible_core.send_line_message(line_token, target_id, f'【每日靈修】\n\n{payload}')
        bible_core.record_entry(payload, f"自動靈修-{chosen_theme}")
    except Exception as e:
        logger.error(f"系統錯誤: {e}")


if __name__ == "__main__":
    main()
