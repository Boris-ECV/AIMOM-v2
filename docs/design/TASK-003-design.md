# TASK-003 系統設計 — 前端 Web 介面
**建立者：** sa-agent | **時間：** 2026-07-09T13:10:00

---

## 架構：單頁 HTML（SPA-like）

單一 `src/frontend/index.html`，內嵌 CSS + JS，無外部依賴。
透過 CSS `display:none/block` 切換 4 個視圖面板。

```
src/frontend/
└── index.html   ← 全部 HTML / CSS / JS 整合
```

---

## 頁面視圖結構

```
#view-upload    ← 初始狀態
#view-progress  ← 處理中（輪詢 API）
#view-result    ← 結果（紀錄 + 逐字稿 Tab）
```

---

## 全域狀態物件

```js
window.meetingState = {
  jobId: null,          // 上傳後取得
  speakers: {},         // { "SPEAKER_00": "王小明" }
  minutes: null,        // summarize API 回應
  segments: [],         // transcribe/diarize segments
  modified: false,      // 是否有未匯出修改
  pollTimer: null,      // setInterval handle
};
```

---

## 關鍵 JS 函式

| 函式 | 說明 |
|------|------|
| `handleUpload()` | 讀取 File，POST /api/upload，儲存 job_id，轉換 view |
| `startPoll()` | setInterval 每 2s GET /api/status/{jobId} |
| `onStatusUpdate(s)` | 更新進度條，stage=done 時觸發 fetchResults() |
| `fetchResults()` | 依序 GET results，填入 minutes + segments |
| `renderMinutes()` | 渲染 4 區塊到 #view-result |
| `renderTranscript()` | 渲染逐字稿到 #tab-transcript |
| `renameSpeaker(old, new)` | 更新 speakers map + 重新渲染 |
| `enableInlineEdit(el)` | contenteditable + blur 儲存 |
| `exportMarkdown()` | 組合 MD 字串 → Blob URL → download |

---

## UI 色彩系統

```css
--primary: #2563EB      /* 主藍色按鈕 */
--success: #16A34A      /* 完成狀態 */
--warning: #D97706      /* 進行中 */
--bg: #F8FAFC           /* 頁面背景 */
--card: #FFFFFF          /* 卡片背景 */
--border: #E2E8F0        /* 邊框 */
--text: #1E293B          /* 主文字 */
--muted: #64748B         /* 次要文字 */
```
