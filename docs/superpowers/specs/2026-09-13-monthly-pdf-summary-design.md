# 每月經文彙整 PDF 推播 — 設計文件

日期：2026-09-13
狀態：待 Brett 審閱

## 背景與目標

Brett 每個月會手動把 `history_all.html`（`main.py`「下載全部 HTML」功能產生的檔案）用瀏覽器印成 PDF，方便回顧整個月的經文。這個過程完全手動，且用「Microsoft Print to PDF」印出來的檔案因為中文字沒有正確的文字層，變成 8MB 多的圖片檔（無法搜尋、複製文字）。

目標：每月 1 號自動把上個月的經文彙整成一份真正可搜尋的文字型 PDF，推播連結到 LINE 目標群組，不需要 Brett 手動操作。

## 架構

新增一個獨立的 GitHub Actions 排程，跟現有的 `daily_push.yml`（每日經文）完全分開、互不影響：

- **新檔案** `.github/workflows/monthly_summary.yml`：cron 排程設在每月 1 號（例如 `0 1 1 * *`，UTC 01:00 = 台灣時間 09:00）
- **新腳本** `monthly_summary.py`：
  1. 讀 `bible_history.json`，篩出「上個月」（若今天是 9 月，篩 8/1~8/31）所有紀錄
  2. 用類似 `bible_core.generate_html_backup` 的邏輯組出一份 HTML（可以重用既有函式或做一個排版更適合列印的版本）
  3. 用 `xhtml2pdf`（`requirements.txt` 裡本來就有、目前沒被使用的套件）把 HTML 轉成 PDF，並嵌入中文字型（見下一節）
  4. PDF 存到 repo 的 `monthly_summaries/YYYY-MM.pdf`（例如 `monthly_summaries/2026-08.pdf`）
  5. 用既有的 `git-auto-commit-action`（跟 `daily_push.yml` 用的同一種機制）把新產生的 PDF commit 進 repo
  6. 推一則 LINE 訊息到 `TARGET_GROUP_ID`，內容是這個檔案的 GitHub 網頁預覽連結：`https://github.com/brettlintw/daily-bible-bot/blob/main/monthly_summaries/{YYYY-MM}.pdf`（GitHub 本身就有內建的 PDF 預覽功能，點開瀏覽器直接看，不需要另外架設任何下載服務）

## 中文字型

`xhtml2pdf` 預設字型不支援中文（會變成空白或亂碼方塊）。解法：下載一份免費、開源、可商用的中文字型（Noto Sans TC 思源黑體），存進 repo（`fonts/NotoSansTC-Regular.ttf`），用 CSS 的 `@font-face` 指定 `xhtml2pdf` 生成 PDF 時套用這個字型。字型檔是一次性加入，之後每個月產生 PDF 都共用，repo 大小不會因此每月變大。

**風險與驗證方式**：`xhtml2pdf`（底層是 `reportlab`）對中文字型嵌入的支援程度需要實際測試才能確認效果（不同版本行為可能不同）。實作時第一步就是先產生一份測試 PDF、人工檢查中文是否正常顯示，如果 `xhtml2pdf` 嵌入字型效果不理想，才考慮換成 `weasyprint`（Brett 已同意先試 `xhtml2pdf`，不行再說）。

## 檔案大小

每月約 28-31 筆經文，每筆含「內容+章節+領受」約 300-500 字。用真正文字內容產生 PDF（而非圖片），預估單月檔案在數百 KB 內，不會造成 repo 明顯肥大。

## 錯誤處理

- 上個月完全沒有推播紀錄時（理論上不應發生），腳本直接結束，不產生空白 PDF、不推播、不報錯
- PDF 產生或推播過程中發生例外，記 log 到 GitHub Actions 執行紀錄；因為這是「錦上添花」的彙整功能而非每日核心推播，**不**串接 2026-08-31 那套「全部模型都失敗才通知管理員」的 LINE 告警機制，避免告警疲勞——失敗了下個月還會再跑一次，不是不可逆的問題

## 測試方式

不引入自動化測試框架（維持個人專案一貫作法）。手動驗證方式：
1. 本機用假的/少量歷史資料跑一次 `monthly_summary.py`，人工檢查產生的 PDF 中文顯示是否正常、排版是否合理
2. 用 GitHub 的 `workflow_dispatch` 手動觸發一次完整流程（比照 `daily_push.yml` 允許手動觸發的既有作法），確認 PDF 真的被 commit 進 repo、LINE 訊息真的送出、連結點開能正常預覽

## 範圍外

- 不處理歷史上已經產生、Brett 手動列印的舊 PDF 檔案
- 不做「補產生過去缺少的月份」的回溯功能，只從實作完成後的下一個月開始自動產生
- PDF 排版風格維持簡單、跟現有 `generate_html_backup` 的視覺風格一致，不特別另外設計版面美化
