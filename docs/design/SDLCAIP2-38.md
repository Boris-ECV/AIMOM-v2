# 設計文件 — SDLCAIP2-38 匯出 PDF 格式內容顯示為亂碼

## 對應需求規格
G1 已核准的 ticket 描述（SDLCAIP2-38）。根因（requirements-analyst 已確認）：
`src/export.py` 的 `_build_pdf` 使用 `UnicodeCIDFont("MSung-Light")`，該字型
只提供正確的 ToUnicode CMap 對應，但字形程式（glyph outlines）本身**未內嵌**
於輸出的 PDF 檔案，需依賴檢視器本機已安裝對應 CJK 字型才能正確顯示——這正是
使用者回報「亂碼/缺字」的成因。本設計把 PDF 中文渲染改為使用內嵌
TrueType 字型（`TTFont`），使字形程式隨 PDF 檔案一併發布。

範圍外（依 ticket 明列，設計不逾越）：Markdown/純文字/docx 的內容排版邏輯、
中文以外語系字型保證、逐一視覺回歸市面 PDF 檢視器、PDF 版面樣式改版。

## 介面/API 契約
無新增/變更對外 API。`GET /api/export/{job_id}` 與
`GET /api/export/meetings/{meeting_id}`（`format=pdf`）既有請求/回應格式、
狀態碼（200 成功、404 找不到、400 未知 format）完全不變——本故事只調整
`_build_pdf` 內部字型註冊與載入方式，是純粹的實作修正，不是新行為。

## 資料模型
無新增資料模型。本故事不觸及 DynamoDB 資料表或 `minutes` JSON 結構。

新增的是一個**隨程式碼提交的靜態資源檔案**（非資料模型，但明確記錄路徑供
developer 直接依循）：

- 新增字型檔：`src/fonts/NotoSansTC-Regular.ttf`
- 新增授權檔：`src/fonts/NotoSansTC-LICENSE.txt`（OFL 1.1 全文，隨字型檔一併
  提交，明確保留授權出處以利日後稽核）

## 關鍵技術決策

1. **選用 Noto Sans TC（Regular，OFL-1.1 授權）作為內嵌字型，來源
   `https://fonts.google.com/noto/specimen/Noto+Sans+TC`。**
   OFL-1.1 明確允許重製、散布、嵌入至其他文件（包含商業用途），滿足 spec
   依賴段落「需具嵌入授權」的要求；Noto 系列是 Google/Adobe 維護的開放
   專案，涵蓋繁體中文（含常用簡體）字形，符合 spec 範圍（不需保證其他非
   ASCII 語系）。只內嵌 Regular 一個字重——現有 `_build_pdf` 沒有粗體/斜體
   需求（只用 `setFont(_CJK_FONT, size)` 調整字級），依 CONSTITUTION
   「避免不必要的抽象層」，不引入目前用不到的字重。

2. **下載格式指定為 TTF（TrueType outline），不是 OTF（CFF outline）。**
   reportlab 的 `reportlab.pdfbase.ttfonts.TTFont` 是針對 `glyf` outline
   table 實作，對純 CFF outline 的 OTF 檔案支援不完整/不保證正確嵌入；
   Google Fonts 網站上 Noto Sans TC 提供的是 hinted TTF 版本，可直接餵給
   `TTFont`，避免踩到 reportlab 已知的 OTF 相容性坑。

3. **字型檔以絕對路徑載入，用 `pathlib.Path(__file__).parent / "fonts" /
   "NotoSansTC-Regular.ttf"`，不是相對於目前工作目錄的相對路徑。**
   延續 `src/tests/test_ui_copy.py` 讀取 `frontend/index.html` 時已建立的
   `Path(__file__).parent...` 慣例；`export.py` 會在 Lambda（cwd 不保證是
   repo root）與本地 pytest（cwd 可能是 repo root 或 `src/`）兩種環境下被
   匯入，用 `__file__` 相對路徑是唯一在兩種環境都可靠的做法。

4. **字型仍在模組匯入時期（module-level）呼叫一次
   `pdfmetrics.registerFont(...)`，沿用現有 `_CJK_FONT` 常數與呼叫時機不變
   ——只把右手邊從 `UnicodeCIDFont("MSung-Light")` 換成
   `TTFont(_CJK_FONT, str(_CJK_FONT_PATH))`，`_CJK_FONT` 值同時從
   `"MSung-Light"` 改為 `"NotoSansTC"`。**
   維持「模組載入時註冊一次」的既有形狀，把改動侷限在字型來源這一行，
   不擴大 diff 範圍（CONSTITUTION 範圍紀律／程式碼風格：延續既有慣例優先
   於個人偏好）。移除不再使用的
   `from reportlab.pdfbase.cidfonts import UnicodeCIDFont` import，改為
   `from reportlab.pdfbase.ttfonts import TTFont`。

   ```python
   from pathlib import Path

   from reportlab.pdfbase import pdfmetrics
   from reportlab.pdfbase.ttfonts import TTFont

   _CJK_FONT = "NotoSansTC"
   _CJK_FONT_PATH = Path(__file__).parent / "fonts" / "NotoSansTC-Regular.ttf"
   pdfmetrics.registerFont(TTFont(_CJK_FONT, str(_CJK_FONT_PATH)))
   ```

   `_build_pdf` 內部所有 `c.setFont(_CJK_FONT, size)` 呼叫點不需改動，因為
   `_CJK_FONT` 常數名稱維持不變，只是其註冊值改變。

5. **字型檔案體積（Noto Sans TC Regular TTF 完整字集約數 MB～十餘 MB）直接
   提交進 repo，不做子集化（subsetting）或動態下載。**
   reportlab 的 `TTFont` 在產生 PDF 時本來就只會把「該份文件實際用到的字
   形」嵌入輸出檔案（自動子集化），所以最終使用者下載的 PDF 檔案不會因為
   來源字型檔完整而膨脹；成本只在 repo/部署包多了一個較大的靜態檔案。
   Lambda 部署包大小若因此吃緊，屬於基礎設施層面的既有 layer/package 大小
   管理範疇（`infra/layer/`），不在本故事 spec 範圍內處理；若日後成為
   問題應是獨立技術債故事（子集化字型或改用執行期下載）。

6. **測試新增字型內嵌驗證：用 `pypdf` 檢查字型描述子（font descriptor）
   含 `FontFile2`（TrueType 內嵌字形程式的標準 key），而非只驗證文字可
   擷取。** 對應 spec Scenario 1 的機器可驗證條件。具體做法（供 developer
   參考，非強制實作細節）：

   ```python
   def _pdf_font_descriptors(content: bytes) -> list[dict]:
       reader = pypdf.PdfReader(io.BytesIO(content))
       descriptors = []
       for page in reader.pages:
           resources = page.get("/Resources") or {}
           fonts = resources.get("/Font") or {}
           for font_ref in fonts.values():
               font_obj = font_ref.get_object()
               descendant = font_obj.get("/DescendantFonts")
               if descendant:
                   df = descendant[0].get_object()
                   fd = df.get("/FontDescriptor")
               else:
                   fd = font_obj.get("/FontDescriptor")
               if fd:
                   descriptors.append(fd.get_object())
       return descriptors

   def test_export_pdf_embeds_cjk_font():
       ...
       descriptors = _pdf_font_descriptors(resp.content)
       assert any("/FontFile2" in d for d in descriptors)
   ```

   既有的 `test_export_pdf_renders_sections` 等文字擷取測試（迴歸，spec
   Scenario 2）維持不動，繼續用 `_pdf_text()` 驗證中文內容擷取正確——換字
   型不應改變 ToUnicode CMap 的正確性，這條既有測試本身就是最直接的迴歸
   保護。

7. **docx／前端 Markdown／純文字匯出完全不動，作為 spec Scenario 3 的
   迴歸範圍由既有測試（`test_export_docx_*`）覆蓋即可，本故事不新增這些
   格式的測試。** spec 範圍外明列「不調整這些格式內容/排版邏輯」；沒有
   程式碼變動就沒有新增測試的必要，避免無意義的重複覆蓋。

## 開放設計問題（定稿時必須為空）
無。字型選擇（Noto Sans TC / OFL-1.1 / TTF）、檔案放置路徑
（`src/fonts/NotoSansTC-Regular.ttf`）、註冊方式改動、字型內嵌驗證測試手法
均已在本設計中具體決定，developer 可直接依此實作。
