import os
import sys
import logging
from datetime import datetime, timedelta
import bible_core

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

REPO_BLOB_BASE = "https://github.com/brettlintw/daily-bible-bot/blob/main"


def get_previous_month_range(today=None):
    today = today or datetime.now(bible_core.TZ_TW)
    first_of_this_month = today.replace(day=1)
    last_of_prev_month = first_of_this_month - timedelta(days=1)
    prev_year, prev_month = last_of_prev_month.year, last_of_prev_month.month
    start_str = f"{prev_year:04d}-{prev_month:02d}-01"
    end_str = f"{prev_year:04d}-{prev_month:02d}-{last_of_prev_month.day:02d}"
    label = f"{prev_year:04d}-{prev_month:02d}"
    return start_str, end_str, label


def filter_monthly_entries(all_history, start_str, end_str):
    monthly_data = [e for e in all_history if start_str <= e.get("date", "") <= end_str]
    return sorted(monthly_data, key=lambda e: (e.get("date", ""), e.get("time", "")))


def group_by_theme(monthly_data):
    groups = {}
    for entry in monthly_data:
        theme = (entry.get("category") or "").rsplit("-", 1)[-1] or "未分類"
        groups.setdefault(theme, []).append(entry)
    ordered_themes = [t for t in bible_core.THEMES if t in groups]
    extra_themes = [t for t in groups if t not in bible_core.THEMES]
    return [(theme, groups[theme]) for theme in ordered_themes + extra_themes]


def build_grouped_html(monthly_data, label):
    grouped = group_by_theme(monthly_data)
    html_content = f"""<html><head><meta charset="utf-8">
    <style>body {{ font-family: sans-serif; font-size: 16px; line-height: 1.6; padding: 20px; }}
    h1 {{ font-size: 22px; }}
    h2 {{ font-size: 18px; border-bottom: 2px solid #888; padding-bottom: 4px; margin-top: 30px; }}
    .entry {{ border-bottom: 1px solid #ccc; margin-bottom: 20px; padding-bottom: 10px; }}
    .meta {{ color: #555; font-size: 14px; }}</style></head><body>
    <h1>{label} 靈修經文彙整（依主題分類）</h1>"""
    for theme, entries in grouped:
        html_content += f"<h2>{theme}（{len(entries)} 筆）</h2>"
        for h in entries:
            content = h.get('content', '無內容').replace('\n', '<br/>')
            html_content += f"<div class='entry'><div class='meta'>{h.get('date')} {h.get('time')} | {h.get('category')}</div><div>{content}</div></div>"
    html_content += "</body></html>"
    return html_content


def render_pdf(html_content, output_path):
    from weasyprint import HTML
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    HTML(string=html_content).write_pdf(output_path)


def get_output_path(label):
    return f"monthly_summaries/{label}.pdf"


def build():
    start_str, end_str, label = get_previous_month_range()
    monthly_data = filter_monthly_entries(bible_core.load_history(), start_str, end_str)

    if not monthly_data:
        logger.info(f"{label} 沒有任何推播紀錄，跳過")
        return

    output_path = get_output_path(label)
    html_content = build_grouped_html(monthly_data, label)

    try:
        render_pdf(html_content, output_path)
        logger.info(f"{label} PDF 已產生：{output_path}")
    except Exception as e:
        logger.error(f"PDF 產生失敗: {e}")


def notify():
    target_id = os.environ.get('TARGET_GROUP_ID', '').strip()
    line_token = os.environ.get('LINE_TOKEN', '').strip()

    if not all([target_id, line_token]):
        logger.error("缺少 TARGET_GROUP_ID 或 LINE_TOKEN，跳過通知")
        return

    _, _, label = get_previous_month_range()
    output_path = get_output_path(label)

    if not os.path.exists(output_path):
        logger.info(f"{output_path} 不存在（可能上個月無資料或產生失敗），不推播")
        return

    repo_url = f"{REPO_BLOB_BASE}/{output_path}"
    try:
        bible_core.send_line_message(line_token, target_id, f"📖 {label} 經文彙整已產生\n{repo_url}")
    except Exception as e:
        logger.error(f"推播失敗: {e}")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "build"
    if mode == "build":
        build()
    elif mode == "notify":
        notify()
    else:
        logger.error(f"未知的模式: {mode}")


if __name__ == "__main__":
    main()
