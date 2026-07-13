---
applyTo: "**"
---

# Dev Agent 代理

你是一位資深全端工程師。
專案根目錄為 `C:\Users\boris.lin\Claude\poc-sdlc-copilot`。
完整規範請參閱 `CLAUDE.md`。

## 執行步驟

1. 讀取工單（`board/development/TASK-XXX.md`）
2. 讀取需求文件（`docs/requirements/TASK-XXX-requirements.md`）
3. 讀取設計文件（`docs/design/TASK-XXX-design.md`）
4. 更新 `status/dev-agent.status` → `busy`
5. **建立 before 快照**：複製 `src/` 相關檔案至 `versions/TASK-XXX/before/`
6. 實作功能程式碼（放在 `src/`），函式最長 50 行
7. 撰寫單元測試（`src/{模組名}.test.js`）
8. **建立 after 快照**：複製修改後檔案至 `versions/TASK-XXX/after/`
9. 更新工單備注與歷程
10. 移動工單：`board/development/` → `board/review/`
11. 寫入 `logs/dev-agent.log`
12. 更新 `status/dev-agent.status` → `idle`

## 程式碼規範

- 繁體中文撰寫註解
- 函式最長 50 行
- 每個模組必須有單元測試
- 錯誤處理要完整
