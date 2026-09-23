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
from reportlab.pdfbase import pdfmetrics

from app import app
from auth import CurrentUser, get_current_user
import export as export_module
from export import _CJK_FONT, _CONTENT_WIDTH, _build_pdf, _wrap_by_width
import jobstore

client = TestClient(app)


def _docx_paragraph_texts(content: bytes) -> list[str]:
    document = docx.Document(io.BytesIO(content))
    return [p.text for p in document.paragraphs]


def _pdf_text(content: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _pdf_font_descriptors(content: bytes) -> list:
    """SDLCAIP2-38：走訪每頁 /Resources/Font，回傳所有字型的 FontDescriptor。"""
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


def test_export_pdf_embeds_cjk_font():
    """SDLCAIP2-38 Scenario 1：PDF 中文字型須為內嵌字型（含 FontFile2），
    而非僅依賴未內嵌的標準 CID 字型（不需檢視器本機安裝 CJK 字型套件）。"""
    _write_job_result("job-pdf-font-embed")
    resp = client.get("/api/export/job-pdf-font-embed?format=pdf")
    assert resp.status_code == 200
    descriptors = _pdf_font_descriptors(resp.content)
    assert descriptors, "PDF 應至少含一個字型描述子"
    assert any("/FontFile2" in d for d in descriptors), (
        "字型描述子須含 FontFile2（TrueType 內嵌字形程式），"
        "而非僅有未內嵌的標準 CID 字型"
    )


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


def _write_kept_meeting(job_id: str, filename: str = "weekly-sync.mp3") -> str:
    """建立一筆 job 並保留，回傳 meeting_id。"""
    jobstore.create_job(
        job_id,
        stage="done",
        progress=100,
        message="done",
        filename=filename,
        segments=[{"speaker": "A", "text": "hello"}],
        minutes={
            "summary": "本次會議討論了專案時程",
            "action_items": [
                {"owner": "Alice", "task": "整理需求文件", "due": "2026-08-01"}
            ],
            "decisions": ["採用 AWS Lambda 部署"],
        },
    )
    resp = client.post(f"/api/meetings/{job_id}/keep")
    assert resp.status_code == 200
    return resp.json()["meeting_id"]


def test_export_kept_meeting_docx_success():
    meeting_id = _write_kept_meeting("job-kept-docx")
    resp = client.get(f"/api/export/meetings/{meeting_id}?format=docx")
    assert resp.status_code == 200
    assert (
        resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert resp.headers["content-disposition"] == f'attachment; filename="{meeting_id}.docx"'
    texts = _docx_paragraph_texts(resp.content)
    assert "會議紀錄 - weekly-sync.mp3" in texts


def test_export_kept_meeting_pdf_success():
    meeting_id = _write_kept_meeting("job-kept-pdf")
    resp = client.get(f"/api/export/meetings/{meeting_id}?format=pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.headers["content-disposition"] == f'attachment; filename="{meeting_id}.pdf"'
    assert resp.content.startswith(b"%PDF")
    text = _pdf_text(resp.content)
    assert "weekly-sync.mp3" in text


def test_export_kept_meeting_defaults_to_docx():
    meeting_id = _write_kept_meeting("job-kept-default-format")
    resp = client.get(f"/api/export/meetings/{meeting_id}")
    assert resp.status_code == 200
    assert (
        resp.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def test_export_kept_meeting_invalid_format_returns_400():
    meeting_id = _write_kept_meeting("job-kept-bad-format")
    resp = client.get(f"/api/export/meetings/{meeting_id}?format=xml")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "format 僅支援 docx 或 pdf"


def test_export_nonexistent_meeting_returns_404():
    resp = client.get("/api/export/meetings/does-not-exist?format=docx")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "找不到此會議紀錄"


def test_export_other_users_meeting_returns_404():
    meeting_id = _write_kept_meeting("job-kept-other-user")

    def _other_user() -> CurrentUser:
        return CurrentUser(email="other-user@example.com", role="user")

    def _owner_user() -> CurrentUser:
        return CurrentUser(email="test-user@example.com", role="user")

    app.dependency_overrides[get_current_user] = _other_user
    try:
        resp = client.get(f"/api/export/meetings/{meeting_id}?format=docx")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides[get_current_user] = _owner_user


def test_export_kept_meeting_reflects_latest_edit_after_patch():
    """銜接 SDLCAIP2-19 AC3：PATCH 編輯後，匯出內容為最新版本。"""
    meeting_id = _write_kept_meeting("job-kept-edited")

    new_minutes = {"summary": "編輯後的摘要", "action_items": [], "decisions": []}
    patch_resp = client.patch(f"/api/meetings/{meeting_id}", json=new_minutes)
    assert patch_resp.status_code == 200

    resp = client.get(f"/api/export/meetings/{meeting_id}?format=docx")
    assert resp.status_code == 200
    texts = _docx_paragraph_texts(resp.content)
    assert "編輯後的摘要" in texts


# --- SDLCAIP2-43：PDF 匯出寬度感知換行 ---------------------------------


def test_wrap_by_width_mixed_cjk_english_lines_never_exceed_content_width():
    """Scenario 1：中英文混合內容換行後，每一行以 NotoSansTC 字型、12pt
    量測的渲染寬度皆不超過 _CONTENT_WIDTH（頁寬扣除左右邊界）。"""
    text = (
        "本次會議討論了 ProjectRoadmapAndDeliverySchedule 相關議題，"
        "並確認 ContinuousIntegrationPipeline 的建置時程，同時檢討了"
        "MicroserviceArchitectureMigrationPlan 的風險與因應對策，"
        "希望能在下一季完成主要里程碑並持續追蹤進度。"
    )
    lines = _wrap_by_width(text)
    assert len(lines) > 1, "測試內容應足以觸發換行"
    for line in lines:
        assert pdfmetrics.stringWidth(line, _CJK_FONT, 12) <= _CONTENT_WIDTH, (
            f"換行後該行渲染寬度超出頁面可用內容寬度：{line!r}"
        )
    # 換行不應遺漏或重複文字：所有片段接回應與原字串一致
    assert "".join(lines) == text


def test_wrap_by_width_does_not_split_english_word_mid_token():
    """Scenario 2：接近換行邊界的完整英文單字/專有名詞，換行後必須完整
    出現在同一行，不得被拆成兩個片段分散在相鄰兩行。"""
    long_word = "ConfigurationManagementSystem"
    # 前置中文文字刻意填到接近單行寬度上限，讓該英文單字落在換行邊界附近。
    filler = "中文填充文字內容" * 6
    text = f"{filler}{long_word}後續補充說明文字"
    lines = _wrap_by_width(text)

    assert long_word in "".join(lines)  # 內容不遺漏
    matches = [line for line in lines if long_word in line]
    assert len(matches) == 1, (
        f"英文單字應完整落在單一行內，不應被拆成片段分散在多行：{lines!r}"
    )
    # 確認沒有任何一行只含該單字的片段（例如被截斷成 "Configuration" 與
    # "ManagementSystem" 分屬兩行）
    for i in range(len(lines) - 1):
        joined_boundary = lines[i] + lines[i + 1]
        if long_word in joined_boundary and long_word not in lines[i] and long_word not in lines[i + 1]:
            pytest.fail(f"英文單字被硬拆到相鄰兩行：{lines[i]!r} / {lines[i + 1]!r}")


def test_build_pdf_wraps_long_decision_and_action_item_within_width():
    """Scenario 3：決定事項／待辦事項（含前綴）長度超出單行寬度時，須換
    行顯示在多行，且每一行渲染寬度皆不超過頁面可用內容寬度。修正前
    _build_pdf 對這兩個欄位直接呼叫 _line()，完全未換行。"""
    long_decision = (
        "採用 AmazonWebServicesElasticComputeCloudLambdaFunctionsServerless "
        "作為主要部署平台，並導入自動擴展與容錯移轉機制以確保服務穩定性"
    )
    minutes = {
        "summary": "摘要",
        "decisions": [long_decision],
        "action_items": [
            {
                "owner": "Alice",
                "task": (
                    "完成 ContinuousIntegrationAndContinuousDeploymentPipeline "
                    "的建置與相關文件撰寫，並與各團隊同步時程安排"
                ),
                "due": "2026-08-01",
            }
        ],
    }
    content = _build_pdf(minutes, "job-long-items")
    text = _pdf_text(content)
    lines = [line for line in text.split("\n") if line.strip()]

    over_width_lines = [
        line
        for line in lines
        if pdfmetrics.stringWidth(line, _CJK_FONT, 12) > _CONTENT_WIDTH
    ]
    assert not over_width_lines, (
        f"決定事項/待辦事項換行後仍有行寬超出頁面可用內容寬度：{over_width_lines!r}"
    )

    decision_lines = [line for line in lines if line.startswith("- 採用")]
    action_lines = [line for line in lines if "Alice" in line]
    assert len(decision_lines) >= 1
    assert any("AmazonWebServicesElasticComputeCloudLambdaFunctionsServerless" in l for l in lines)
    assert any("ContinuousIntegrationAndContinuousDeploymentPipeline" in l for l in lines)
    # 內容須被拆成多行顯示（而非單行超出頁面邊界）
    assert len(lines) > 5


def test_build_pdf_wraps_long_meeting_info_participants_within_width():
    """Scenario 5：會議資訊之參與者清單過長時，須換行顯示在多行，且每一
    行渲染寬度皆不超過頁面可用內容寬度。修正前 _build_pdf 對會議資訊直
    接呼叫 _line()，完全未換行，長參與者清單會超出頁面邊界。"""
    many_participants = [f"參與者姓名{i:03d}" for i in range(40)]
    minutes = {
        "meeting_info": {
            "date": "2026-09-23",
            "time": "14:00",
            "location": "會議室 A",
            "participants": many_participants,
        },
        "summary": "摘要",
        "decisions": [],
        "action_items": [],
    }
    content = _build_pdf(minutes, "job-long-participants")
    text = _pdf_text(content)
    lines = [line for line in text.split("\n") if line.strip()]

    over_width_lines = [
        line
        for line in lines
        if pdfmetrics.stringWidth(line, _CJK_FONT, 12) > _CONTENT_WIDTH
    ]
    assert not over_width_lines, (
        f"會議資訊換行後仍有行寬超出頁面可用內容寬度：{over_width_lines!r}"
    )

    participant_lines = [line for line in lines if "參與者" in line or "參與者姓名" in line]
    assert len(participant_lines) > 1, "參與者清單應被拆成多行顯示，而非單行超出頁面邊界"
    assert any("參與者姓名000" in l for l in lines)
    assert any("參與者姓名039" in l for l in lines)


def test_export_pdf_short_cjk_and_english_content_roundtrips_unchanged():
    """Scenario 4（迴歸）：摘要、決定事項、待辦事項、討論重點皆為單行寬
    度以內的短文字時，PDF 文字層擷取結果仍與原始內容一致，換行邏輯調整
    不應造成文字遺漏或重複。"""
    jobstore.create_job(
        "job-pdf-short-regression",
        stage="done",
        progress=100,
        message="done",
        minutes={
            "summary": "本次會議討論了專案時程",
            "decisions": ["採用 AWS Lambda 部署"],
            "action_items": [
                {"owner": "Alice", "task": "整理需求文件", "due": "2026-08-01"}
            ],
            "sections": [{"title": "Keep", "content": "維持每週同步會議"}],
        },
    )
    resp = client.get("/api/export/job-pdf-short-regression?format=pdf")
    assert resp.status_code == 200
    text = _pdf_text(resp.content)

    assert text.count("本次會議討論了專案時程") == 1
    assert text.count("採用 AWS Lambda 部署") == 1
    assert "Alice" in text
    assert text.count("整理需求文件") == 1
    assert text.count("維持每週同步會議") == 1
