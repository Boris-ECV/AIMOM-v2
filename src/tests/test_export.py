"""TASK-010 測試：多格式匯出（Word/PDF 後端產生）。"""
import pytest
from fastapi.testclient import TestClient

from app import app
import jobstore

client = TestClient(app)


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
