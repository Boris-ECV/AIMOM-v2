# 設計文件 — SDLCAIP2-31 [SECURITY] 講者重新命名輸入框渲染未轉義使用者輸入，DOM-based XSS 風險

## 對應需求規格
對應 SDLCAIP2-31 於 G1 通過的定稿需求規格（見 ticket 描述之 Gherkin 驗收條件，共 4 個
Scenario：一般標籤正常渲染、講者標籤含特殊字元被中和、已存在講者名稱含特殊字元被中和、既有
`esc()` 呼叫點不受影響）。

## 介面/API 契約
無 — 本 story 為純前端渲染修正（`src/frontend/index.html` 內 `renderTranscript()` 與
`esc()`），不涉及任何後端 API、路由或請求/回應格式變更。

## 資料模型
無新增資料模型 — 不涉及任何資料表、欄位或索引變更；`state.speakers` 為既有前端 in-memory
物件，結構不變。

## 關鍵技術決策

1. **修正方式：擴充 `esc()`，新增對雙引號 `"` 的轉義（`"` → `&quot;`），而非另建第二個
   helper。**
   - 現況（`src/frontend/index.html:1139-1141`）：
     ```js
     function esc(str) {
       return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
     }
     ```
   - 修正後：
     ```js
     function esc(str) {
       return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
     }
     ```
   - 理由：漏洞的根本原因是 `esc()` 從未轉義 `"`，導致注入 `value="..."` 屬性時可用 `"` 提前
     結束屬性、接上任意屬性（如 `onmouseover=`）。單純把注入值包一層現有 `esc()`（方案 a 的
     子選項）不足以阻斷此向量；必須讓 `esc()` 本身轉義 `"`，一次性堵住所有現有與未來透過
     `esc()` 輸出到雙引號屬性情境的注入點。`&` 的轉義必須放在最前面（已符合現況實作順序），
     否則會把 `&quot;` 中的 `&` 二次轉義成 `&amp;quot;`。

2. **已逐一檢查 `esc()` 現有全部呼叫點，確認新增 `"` → `&quot;` 轉義不會造成任何 side
   effect：**
   - `index.html:781` `esc(a.owner)`、`782` `esc(a.task)`、`783` `esc(a.due)` — 輸出於
     `<td>...</td>` **文字內容**（非屬性值），瀏覽器會將 `&quot;` 還原顯示為 `"` 字元，視覺與
     現行行為完全一致。
   - `index.html:805` `esc(t.title)` — 輸出於 `<div class="topic-header">...</div>` 文字內容，
     同上，無影響。
   - `index.html:807` `esc(t.content)` — 輸出於 `<div class="topic-body">...</div>` 文字內容，
     同上，無影響。
   - `index.html:857` `esc(displayName)`、`859` `esc(seg.text)` — 本 story Scenario 4
     （回歸測試）明確要求的既有呼叫點，同樣是文字內容情境，行為不變。
   - 結論：`esc()` 目前所有呼叫點皆用於 HTML **文字節點**（tag 之間），從未用於屬性值情境；
     新增 `"` 轉義對文字節點渲染結果無任何可觀察差異（`&quot;` 與裸 `"` 在文字節點中渲染結果
     相同），因此可安全地在 `esc()` 內部統一擴充，不需要為屬性情境另建第二個 helper 版本。

3. **兩處注入點的具體修正（`renderTranscript()`，現況 `index.html:828-835`）：**
   - 現況：
     ```js
     uniqueSpeakers.forEach(sp => {
       rows.innerHTML += `
         <div class="rename-row">
           <label>${sp}</label>
           <input type="text" value="${state.speakers[sp] || sp}"
             onchange="renameSpeaker('${sp}', this.value)" placeholder="輸入真實姓名">
         </div>`;
     });
     ```
   - 修正後：
     ```js
     uniqueSpeakers.forEach(sp => {
       rows.innerHTML += `
         <div class="rename-row">
           <label>${esc(sp)}</label>
           <input type="text" value="${esc(state.speakers[sp] || sp)}"
             onchange="renameSpeaker('${esc(sp)}', this.value)" placeholder="輸入真實姓名">
         </div>`;
     });
     ```
   - 兩個注入點：(1) `<label>${sp}</label>` 文字內容 → 改用 `esc(sp)`；
     (2) `value="${state.speakers[sp] || sp}"` 雙引號屬性值 → 改用
     `esc(state.speakers[sp] || sp)`（此為漏洞核心，擴充後的 `esc()` 會把 `"` 轉為
     `&quot;`，使 `element.value` 讀出時仍等於原始字面字串，同時無法提前結束屬性）。
   - 附帶修正 `onchange="renameSpeaker('${sp}', this.value)"` 內的 `sp` 也改用
     `esc(sp)`：雖然驗收條件的 Scenario 只針對 `value` 屬性與 `onmouseover` 提出明確斷言，
     但 `sp` 同時被注入進單引號 inline-handler 屬性，若不轉義會殘留另一條 `'` 破出向量
     （spec 給定的攻擊字串本身不含 `'`，故不影響驗收條件通過，但放著不修等同留下已知同類
     漏洞）。此為本設計依既有測資之外、依安全常規補強的判斷，不影響任何驗收 Scenario 的
     斷言結果。

4. **不改變 DOM 結構，僅改變寫入 `innerHTML` 的字串內容。** 符合 Scenario 1／4 對「不改變
   既有 markup/屬性集合、不影響既有 `esc()` 呼叫點行為」的要求 —
   `<input>` 元素最終仍只有 `type`、`value`、`onchange`、`placeholder` 四個屬性。

## 開放設計問題（定稿時必須為空）
（無）
