# 設計文件 — SDLCAIP2-34 從管理者儀表板返回上傳頁後，上傳按鈕錯誤顯示「上傳中」

## 對應需求規格
G1 已核准的 ticket 描述（SDLCAIP2-34）：使用者成功上傳一次錄音檔後，若導覽到
管理者儀表板（`view-admin`）再返回上傳頁（`view-upload`），上傳按鈕
（`#upload-btn`）會停留在上一次上傳時設定的「上傳中...」文字與
`disabled` 狀態，即使當下並無任何上傳正在進行。範圍外：不做上傳流程整體
重構、不變更其他頁面的狀態管理、不變更按鈕本身的 UI／文案樣式，僅修正
「返回上傳頁時殘留錯誤狀態」這個缺陷本身。

## 根因分析（依 `src/frontend/index.html` 目前程式碼逐行核對）

- `doUpload()`（第 923–972 行）在函式一開始（第 925–926 行）把
  `#upload-btn` 設為 `disabled = true`、文字改成「上傳中...」。
  - 失敗路徑（`catch` 區塊，第 967–971 行）**有**把按鈕還原成
    `disabled = false`、文字「開始處理」。
  - 成功路徑（第 954–966 行：拿到 `data.job_id` 之後）**沒有**還原按鈕
    狀態，而是直接 `showView('view-progress')`（第 959 行）並開始輪詢
    （`startPoll()`）——`view-upload` 這個 DOM 只是被隱藏（CSS class
    切換，見 `showView()` 第 1457–1460 行），按鈕殘留的「上傳中...」／
    `disabled=true` 狀態並未被清除，就留在 DOM 裡。
- 管理者儀表板的「← 返回」按鈕（第 205 行）：
  `onclick="showView('view-upload')"`，只做 CSS active class 切換，
  沒有呼叫任何狀態重置函式。
- `resetState()`（第 1433–1446 行）是目前程式碼中唯一正確「重置所有上傳
  相關按鈕狀態」的函式（第 1443–1444 行明確把 `#upload-btn` 設回
  `disabled=true`、文字「開始處理」），目前呼叫者只有：
  - `cleanupAndReset()`（第 1416–1425 行）
  - `cancelJob()`（第 1427–1431 行）

  兩者都是「使用者主動放棄/清除當前 job」的情境，呼叫 `resetState()` 時
  `state.jobId` 一定已經確定不再需要（`cleanupAndReset` 已呼叫
  DELETE API；`cancelJob` 已清掉輪詢計時器）。

結論：問題根源在 `doUpload()` 成功路徑從未還原按鈕狀態，而不是「返回」
按鈕本身的邏輯有錯——`showView('view-upload')` 只是讓這個已經殘留錯誤
狀態的 DOM 重新可見而已。

## 介面/API 契約
不涉及對外 HTTP API，純前端 JS 函式行為變更。

### 現況（`doUpload()` 第 954–960 行）
```js
const data = await completeRes.json();
if (!completeRes.ok) throw new Error(data.detail || '上傳失敗');

state.jobId = data.job_id;
localStorage.setItem('meetingJobId', state.jobId);
showView('view-progress');
startPoll();
```

### 變更後
```js
const data = await completeRes.json();
if (!completeRes.ok) throw new Error(data.detail || '上傳失敗');

resetState();                                   // 新增：上傳成功，還原上傳頁按鈕/欄位狀態
state.jobId = data.job_id;                      // 必須在 resetState() 之後才賦值
localStorage.setItem('meetingJobId', state.jobId);
showView('view-progress');
startPoll();
```

`resetState()`、`showView()`、`cleanupAndReset()`、`cancelJob()`、管理者
儀表板返回按鈕（第 205 行）、`view-result` 的「+ 新錄音」按鈕（第 301
行）**函式簽章與呼叫方式全部不變**——本次修正只在 `doUpload()` 成功路徑
新增一行 `resetState()` 呼叫，並把既有的
`state.jobId = data.job_id;` 移到這行呼叫之後。

### 狀態碼
不變，本故事不涉及任何後端端點。

## 資料模型
無新增/變更資料模型。純前端狀態物件（`state`）與既有函式重用，不涉及
任何資料表、欄位、索引或 job 記錄結構變更。

## 關鍵技術決策

1. **修正點選在 `doUpload()` 成功路徑本身，而非管理者儀表板返回按鈕的
   `onclick`、也不是 `showView()` 內部加判斷。**
   理由：`doUpload()` 是目前程式碼中唯一一個「離開 `view-upload` 且不經過
   `resetState()`」的路徑，把重置動作放在這裡是一次性修正根因，不需要在
   每一個「導覽回 view-upload」的入口（管理者儀表板返回鍵、第 301 行
   「+ 新錄音」鍵、未來可能新增的其他入口）各自補呼叫，避免掛一漏萬。
   反之若改成在管理者儀表板返回按鈕或 `showView()` 裡呼叫
   `resetState()`，會產生一個真實的競態風險：使用者可能在 `doUpload()`
   仍在等待 `/api/upload/presign`／S3 PUT／`/api/upload/complete`
   （此時人仍停留在 `view-upload`、按鈕顯示「上傳中...」，但
   `state.jobId` 尚未賦值）期間，點擊 header 常駐的管理者儀表板按鈕離開
   再返回——此時若返回動作觸發 `resetState()`，會把仍在進行中的
   `state.file` 清成 `null`，而 `doUpload()` 內後續程式碼仍會用
   `state.file.name` 等欄位，將丟出未預期的例外。把重置動作放在
   `doUpload()` 自己「已經確定上傳成功、不會再用到 `state.file`」的那一
   行，完全不存在這個時間窗，不需要額外引入新的旗標（如
   `state.uploading`）去防呆。

2. **重用既有 `resetState()`，不在 `doUpload()` 內另外手動重置
   `#upload-btn` 的 `disabled`/文字。**
   理由：ticket 明確要求走「重用既有 `resetState()`」這條路徑；
   `resetState()`（第 1443–1444 行）已經是「把上傳頁按鈕狀態還原成初始
   值」的唯一權威實作，`cleanupAndReset()`／`cancelJob()`
   已在用同一個函式做同樣的事。若在 `doUpload()` 內另外手寫兩行
   `btn.disabled=true; btn.textContent='開始處理';`，會與 `resetState()`
   內的對應程式碼重複，未來若两处修改按鈕文案只改了一處會產生不一致。

3. **`resetState()` 呼叫必須放在 `state.jobId = data.job_id;` 之前，並把
   原本這行的賦值挪到 `resetState()` 呼叫之後。**
   理由：`resetState()` 內部會執行 `state.jobId = null` 與
   `localStorage.removeItem('meetingJobId')`（第 1434、1441
   行），若順序顛倒（先賦值新 `jobId` 再呼叫 `resetState()`），剛設定好
   的新 job id 會被立刻清空，導致 `showView('view-progress')` 之後的
   `startPoll()` 拿不到 `state.jobId`，直接破壞上傳成功後的既有正常流程。

4. **`resetState()` 內連帶清除的 `state.file`／`state.modified`／
   `state.segments`／`state.minutes`／`state.speakers`／
   `state.summarizeTriggered`／`file-info` 顯示／`progress-bar` 寬度等其他
   欄位，在上傳成功的當下清空皆屬安全、預期中的副作用，不需要另外篩選只
   清按鈕欄位。**
   理由：這些欄位本來就是「上一次上傳」的殘留資料，上傳成功、即將進入
   `view-progress`／後續全新一輪流程時本來就該歸零（`cleanupAndReset()`
   與 `cancelJob()` 呼叫 `resetState()` 時同樣是整批歸零，行為一致）；
   `progress-bar` 歸零、`file-info` 隱藏也不影響 `view-progress`（該視圖
   有自己的進度顯示邏輯，不依賴 `view-upload` 裡的 `#file-info`／
   `#progress-bar`）。

5. **管理者儀表板返回按鈕（第 205 行）、`showView()`（第 1457–1460
   行）、「+ 新錄音」按鈕（第 301 行）程式碼維持原樣，不額外增加呼叫。**
   理由：修正點 1 已經是根因層級的一次性修正，這些入口本身邏輯（單純的
   `showView()` 切換）沒有缺陷，額外去改動它們屬於 ticket 範圍外的「一般
   性上傳流程重構」，且會增加不必要的改動面。

## 開放設計問題（定稿時必須為空）
無。根因、修正位置與呼叫順序均可由既有程式碼結構與 ticket 描述直接推定，
未發現規格未決的產品決策。
