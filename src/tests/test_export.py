"""TASK-010 測試：多格式匯出（Word/PDF 後端產生）。"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import app
import config


def _write_job_result(tmp_path: Path, job_id: str):
    job_dir = tmp_path / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "minutes.json").write_text(
        json.dumps(
            {
                "summary": "本次會議討論了專案時程",
                "action_items": [
                    {"owner": "Alice", "task": "整理需求文件", "due": "2026-08-01"}
                ],
                "decisions": ["採用 AWS Lambda 部署"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "TMP_DIR", str(tmp_path))
    return TestClient(app)


def test_export_docx_success(client, tmp_path):
    _write_job_result(tmp_path, "job-docx")
    resp = client.get("/api/export/job-docx?format=docx")
    assert resp.status_code == 200
    assert (
        resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert len(resp.content) > 0


def test_export_pdf_success(client, tmp_path):
    _write_job_result(tmp_path, "job-pdf")
    resp = client.get("/api/export/job-pdf?format=pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


def test_export_missing_job_returns_404(client):
    resp = client.get("/api/export/does-not-exist?format=docx")
    assert resp.status_code == 404


def test_export_invalid_format_returns_400(client, tmp_path):
    _write_job_result(tmp_path, "job-bad")
    resp = client.get("/api/export/job-bad?format=xml")
    assert resp.status_code == 400
