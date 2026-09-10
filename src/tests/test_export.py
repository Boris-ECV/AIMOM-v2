"""TASK-010 測試：多格式匯出（Word/PDF 後端產生）。

SDLCAIP2-15 補強：test_export_docx_renders_sections /
test_export_pdf_renders_sections 原本只驗證 HTTP 200 + non-empty bytes，
不足以驗證 AC2（「討論重點」標題、每個 section 的 title/content 文字
實際出現在匯出文件內容中）。改用 python-docx 解析 docx 段落文字；PDF
則用 pypdf 抽取文字層（環境已確認可用，見下方匯入）。
"""
import io

import docx
import pypdf
import pytest
from fastapi.testclient import TestClient

from app import app
import jobstore

client = TestClient(app)


def _docx_paragraph_texts(content: bytes) -> list[str]:
    document = docx.Document(io.BytesIO(content))
    return [p.text for p in document.paragraphs]


def _pdf_text(content: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _write_job_result(job_id: str):
    jobstore.create_job(
        job_id,
        stage="done",
        progress=100,
        message="done",
        minutes={
            "summary": "本次會議討論了專案時程",
            "action_items": [
                {"owner": "Alice", "task": "整理需求文件", "due": "2026-08-01"}
            ],
            "decisions": ["採用 AWS Lambda 部署"],
        },
    )


def test_export_docx_success():
    _write_job_result("job-docx")
    resp = client.get("/api/export/job-docx?format=docx")
    assert resp.status_code == 200
    assert (
        resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert len(resp.content) > 0


def test_export_pdf_success():
    _write_job_result("job-pdf")
    resp = client.get("/api/export/job-pdf?format=pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


def test_export_missing_job_returns_404():
    resp = client.get("/api/export/does-not-exist?format=docx")
    assert resp.status_code == 404


def test_export_invalid_format_returns_400():
    _write_job_result("job-bad")
    resp = client.get("/api/export/job-bad?format=xml")
    assert resp.status_code == 400


def test_export_docx_renders_sections():
    """AC2（docx）：討論重點標題 + 每個 section 的 title/content 文字
    須實際出現在 docx 段落內容中，不只是 HTTP 200/non-empty bytes。"""
    jobstore.create_job(
        "job-docx-sections",
        stage="done",
        progress=100,
        message="done",
        minutes={
            "summary": "摘要",
            "action_items": [],
            "decisions": [],
            "sections": [
                {"title": "Keep", "content": "維持每週同步會議"},
                {"title": "Problem", "content": "需求變動頻繁"},
            ],
        },
    )
    resp = client.get("/api/export/job-docx-sections?format=docx")
    assert resp.status_code == 200
    texts = _docx_paragraph_texts(resp.content)
    assert "討論重點" in texts
    assert "Keep" in texts
    assert "維持每週同步會議" in texts
    assert "Problem" in texts
    assert "需求變動頻繁" in texts


def test_export_pdf_renders_sections():
    """AC2（pdf）：同上，改用 pypdf 抽取文字層驗證。"""
    jobstore.create_job(
        "job-pdf-sections",
        stage="done",
        progress=100,
        message="done",
        minutes={
            "summary": "摘要",
            "action_items": [],
            "decisions": [],
            "sections": [{"title": "Keep", "content": "維持每週同步會議"}],
        },
    )
    resp = client.get("/api/export/job-pdf-sections?format=pdf")
    assert resp.status_code == 200
    assert resp.content.startswith(b"%PDF")
    text = _pdf_text(resp.content)
    assert "討論重點" in text
    assert "Keep" in text
    assert "維持每週同步會議" in text


def test_export_docx_renders_sections_placeholder_when_empty():
    """AC3（docx edge case）：sections 為空/缺失時，仍輸出「討論重點」
    標題 + 「（無）」佔位段落。"""
    jobstore.create_job(
        "job-docx-no-sections",
        stage="done",
        progress=100,
        message="done",
        minutes={"summary": "摘要", "action_items": [], "decisions": []},
    )
    resp = client.get("/api/export/job-docx-no-sections?format=docx")
    assert resp.status_code == 200
    texts = _docx_paragraph_texts(resp.content)
    assert "討論重點" in texts
    heading_idx = texts.index("討論重點")
    assert texts[heading_idx + 1] == "（無）"


def test_export_pdf_renders_sections_placeholder_when_empty():
    """AC3（pdf edge case）：同上。"""
    jobstore.create_job(
        "job-pdf-no-sections",
        stage="done",
        progress=100,
        message="done",
        minutes={"summary": "摘要", "action_items": [], "decisions": [], "sections": []},
    )
    resp = client.get("/api/export/job-pdf-no-sections?format=pdf")
    assert resp.status_code == 200
    text = _pdf_text(resp.content)
    assert "討論重點" in text
    assert "（無）" in text
