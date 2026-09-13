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
  3. 用 `weasyprint` 把 HTML 轉成 PDF（見下一節「中文字型」，說明為什麼選這套而不是 `xhtml2pdf`）
  4. PDF 存到 repo 的 `monthly_summaries/YYYY-MM.pdf`（例如 `monthly_summaries/2026-08.pdf`）
  5. 用既有的 `git-auto-commit-action`（跟 `daily_push.yml` 用的同一種機制）把新產生的 PDF commit 進 repo
  6. 推一則 LINE 訊息到 `TARGET_GROUP_ID`，內容是這個檔案的 GitHub 網頁預覽連結：`https://github.com/brettlintw/daily-bible-bot/blob/main/monthly_summaries/{YYYY-MM}.pdf`（GitHub 本身就有內建的 PDF 預覽功能，點開瀏覽器直接看，不需要另外架設任何下載服務）

## 中文字型：改用 `weasyprint`，不用 `xhtml2pdf`

**2026-09-13 實測結果**：原本計畫用 `requirements.txt` 裡現成的 `xhtml2pdf` 搭配嵌入字型檔。實際下載一份正版 Noto Sans TC 字型、用 `xhtml2pdf` 嵌入測試後，產生的 PDF 沒有報錯，但把 PDF 渲染成圖片人工檢查，中文字全部變成黑色方塊（「豆腐字」），完全沒有正確顯示——這是 `xhtml2pdf` 底層 `reportlab` 對中文字型嵌入支援不足的已知限制，不是設定錯誤。因此**放棄 `xhtml2pdf`，改用 `weasyprint`**。

`weasyprint` 底層用 Linux 的 Pango 文字排版引擎，對中文的支援業界公認成熟許多。改用它之後**不需要在 repo 裡管理任何字型檔**——GitHub Actions 的執行環境是 Ubuntu，在 workflow 裡加一行 `apt-get install -y fonts-noto-cjk` 安裝系統字型，`weasyprint` 會透過 fontconfig 自動抓到中文字型使用，比原本「下載字型檔存進 repo + CSS 手動指定」的做法更簡單。

`requirements.txt` 需要新增 `weasyprint` 這個套件（`xhtml2pdf` 維持保留在檔案裡，因為現有 `CLAUDE.md` 已經註記它是「疑似遺留依賴，不確定是否還有計畫用到」，這次沒用到它，不代表要順手移除，移除與否留給 Brett 之後決定）。

**風險與後續驗證**：`weasyprint` 需要的 Linux 圖形函式庫在開發用的 Windows 機器上裝不起來，沒辦法在本機做到完整端到端測試——這條路徑在 Ubuntu（GitHub Actions 的執行環境）上是官方文件推薦、廣泛使用的標準做法，但實際能不能動，最終要用 GitHub Actions 的 `workflow_dispatch` 手動觸發一次才能 100% 確認（見「測試方式」一節）。如果屆時仍有問題，再回來討論其他方案。

## 檔案大小

每月約 28-31 筆經文，每筆含「內容+章節+領受」約 300-500 字。用真正文字內容產生 PDF（而非圖片），預估單月檔案在數百 KB 內，不會造成 repo 明顯肥大。

## 錯誤處理

- 上個月完全沒有推播紀錄時（理論上不應發生），腳本直接結束，不產生空白 PDF、不推播、不報錯
- PDF 產生或推播過程中發生例外，記 log 到 GitHub Actions 執行紀錄；因為這是「錦上添花」的彙整功能而非每日核心推播，**不**串接 2026-08-31 那套「全部模型都失敗才通知管理員」的 LINE 告警機制，避免告警疲勞——失敗了下個月還會再跑一次，不是不可逆的問題

## 測試方式

不引入自動化測試框架（維持個人專案一貫作法）。手動驗證方式：
1. 邏輯層面（篩選上個月資料、組 HTML、檔名/路徑產生）可以在本機用假的/少量歷史資料跑過一次，不需要 Ubuntu 環境
2. `weasyprint` 實際轉出來的 PDF 中文顯示是否正常，因為需要 Linux 圖形函式庫，本機（Windows）無法完整測試，**第一次真正驗證要靠 GitHub Actions 的 `workflow_dispatch` 手動觸發**（比照 `daily_push.yml` 允許手動觸發的既有作法），確認 PDF 真的被 commit 進 repo、中文正常顯示、LINE 訊息真的送出、連結點開能正常預覽

## 範圍外

- 不處理歷史上已經產生、Brett 手動列印的舊 PDF 檔案
- 不做「補產生過去缺少的月份」的回溯功能，只從實作完成後的下一個月開始自動產生
- PDF 排版風格維持簡單、跟現有 `generate_html_backup` 的視覺風格一致，不特別另外設計版面美化
