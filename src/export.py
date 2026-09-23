"""多格式匯出 API（TASK-010）。

Word (.docx) 與 PDF 由後端產生；純文字匯出由前端直接產生（不呼叫此 API）。
"""
from __future__ import annotations

import io
import json
import re
from pathlib import Path

from docx import Document
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import db
import jobstore
from auth import CurrentUser, get_current_user

router = APIRouter()

# SDLCAIP2-38：改用內嵌 TrueType 字型（Noto Sans TC，OFL-1.1 授權，見
# fonts/NotoSansTC-LICENSE.txt），取代未內嵌字形程式的 UnicodeCIDFont，
# 避免 PDF 檢視器未安裝對應 CJK 字型時顯示亂碼/缺字。
#
# 檔名雖為 "-Regular"，但實際內容是 Google Fonts 目前對 Noto Sans TC
# 唯一提供的可變字重（variable-weight）字型檔——Google 已不再單獨發布
# 靜態 Regular 字重的 TTF。沿用此檔名是為了與 docs/design/SDLCAIP2-38.md
# 的既定路徑保持一致，而非誤植成靜態字重版本。已獨立驗證（2026-09-18，
# tester 子代理於乾淨環境重跑）：此檔案是合法、未損壞的 TrueType（sfnt
# magic bytes 正確），reportlab 的 TTFont 可正常載入並嵌入 PDF，字型描
# 述子含 FontFile2，文字擷取結果正確——僅內部 face name 顯示為
# "NotoSansTC-Thin"（可變字重中繼資料的產物），純屬命名巧合，不影響任
# 何驗收條件。
_CJK_FONT = "NotoSansTC"
_CJK_FONT_PATH = Path(__file__).parent / "fonts" / "NotoSansTC-Regular.ttf"
pdfmetrics.registerFont(TTFont(_CJK_FONT, str(_CJK_FONT_PATH)))

# SDLCAIP2-43：可用內容寬度＝頁寬扣除左右邊界（右邊界比照既有左邊界同為
# 50pt，詳見 docs/design/SDLCAIP2-43.md 技術決策 2）。
_PAGE_MARGIN_L = 50
_PAGE_MARGIN_R = 50
_CONTENT_WIDTH = A4[0] - _PAGE_MARGIN_L - _PAGE_MARGIN_R

# ASCII 英數字連續片段視為一個不可切割的 token（英文單字/專有名詞不被硬
# 拆），其餘字元（CJK 字、標點、空白）各自成一個 token，詳見技術決策 3。
_WORD_TOKEN_RE = re.compile(r"[A-Za-z0-9]+|[^A-Za-z0-9]")


def _load_minutes(job_id: str) -> dict:
    job = jobstore.get_job(job_id)
    if job is None or job.get("minutes") is None:
        raise HTTPException(status_code=404, detail="找不到會議紀錄，請先完成 /summarize")
    return job["minutes"]


def _meeting_info_lines(minutes: dict) -> list[str]:
    """把 meeting_info 轉成顯示用的一行行文字，未提及欄位顯示「未提及」。"""
    info = minutes.get("meeting_info") or {}
    date = info.get("date") or "未提及"
    time = info.get("time") or "未提及"
    location = info.get("location") or "未提及"
    participants = info.get("participants") or []
    participants_text = "、".join(participants) if participants else "未提及"
    return [
        f"日期：{date}",
        f"時間：{time}",
        f"地點：{location}",
        f"參與者：{participants_text}",
    ]


def _build_docx(minutes: dict, heading: str) -> bytes:
    doc = Document()
    doc.add_heading(f"會議紀錄 - {heading}", level=1)

    doc.add_heading("會議資訊", level=2)
    for line in _meeting_info_lines(minutes):
        doc.add_paragraph(line, style="List Bullet")

    doc.add_heading("摘要", level=2)
    doc.add_paragraph(minutes.get("summary", ""))

    doc.add_heading("決定事項", level=2)
    decisions = minutes.get("decisions", [])
    if decisions:
        for d in decisions:
            doc.add_paragraph(d, style="List Bullet")
    else:
        doc.add_paragraph("（無）")

    doc.add_heading("待辦事項", level=2)
    action_items = minutes.get("action_items", [])
    if action_items:
        for item in action_items:
            owner = item.get("owner", "-")
            task = item.get("task", "-")
            due = item.get("due", "-")
            doc.add_paragraph(f"[{owner}] {task}（期限：{due}）", style="List Bullet")
    else:
        doc.add_paragraph("（無）")

    doc.add_heading("討論重點", level=2)
    sections = minutes.get("sections", [])
    if sections:
        for s in sections:
            doc.add_heading(s.get("title", ""), level=3)
            doc.add_paragraph(s.get("content", "") or "（無）")
    else:
        doc.add_paragraph("（無）")

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


def _build_pdf(minutes: dict, heading: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 60

    def _line(text: str, size: int = 12, gap: int = 20):
        nonlocal y
        c.setFont(_CJK_FONT, size)
        c.drawString(_PAGE_MARGIN_L, y, text)
        y -= gap
        if y < 60:
            c.showPage()
            y = height - 60

    _line(f"會議紀錄 - {heading}", size=16, gap=30)

    _line("會議資訊", size=14, gap=22)
    for line in _meeting_info_lines(minutes):
        _line(line)

    _line("摘要", size=14, gap=22)
    for chunk in _wrap_by_width(minutes.get("summary", "")):
        _line(chunk)

    _line("決定事項", size=14, gap=22)
    decisions = minutes.get("decisions", [])
    if decisions:
        for d in decisions:
            for chunk in _wrap_by_width(f"- {d}"):
                _line(chunk)
    else:
        _line("（無）")

    _line("待辦事項", size=14, gap=22)
    action_items = minutes.get("action_items", [])
    if action_items:
        for item in action_items:
            owner = item.get("owner", "-")
            task = item.get("task", "-")
            due = item.get("due", "-")
            for chunk in _wrap_by_width(f"- [{owner}] {task}（期限：{due}）"):
                _line(chunk)
    else:
        _line("（無）")

    _line("討論重點", size=14, gap=22)
    sections = minutes.get("sections", [])
    if sections:
        for s in sections:
            for chunk in _wrap_by_width(s.get("title", ""), size=13):
                _line(chunk, size=13, gap=18)
            for chunk in _wrap_by_width(s.get("content", "") or "（無）"):
                _line(chunk)
    else:
        _line("（無）")

    c.save()
    buf.seek(0)
    return buf.read()


def _wrap_by_width(
    text: str,
    max_width: float = _CONTENT_WIDTH,
    font: str = _CJK_FONT,
    size: int = 12,
) -> list[str]:
    """依實際渲染寬度換行，ASCII 英數字連續片段（英文單字/專有名詞）不被
    從中間拆開，詳見 docs/design/SDLCAIP2-43.md。"""
    if not text:
        return [""]
    tokens = _WORD_TOKEN_RE.findall(text)
    lines: list[str] = []
    current = ""
    for tok in tokens:
        candidate = current + tok
        if current and pdfmetrics.stringWidth(candidate, font, size) > max_width:
            lines.append(current)
            current = "" if tok.isspace() else tok
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


@router.get("/export/{job_id}")
async def export_meeting(
    job_id: str, format: str = "docx", user: CurrentUser = Depends(get_current_user)
):
    """匯出指定 job 的會議紀錄。format 支援 docx / pdf。"""
    minutes = _load_minutes(job_id)

    if format == "docx":
        content = _build_docx(minutes, job_id)
        media_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        filename = f"{job_id}.docx"
    elif format == "pdf":
        content = _build_pdf(minutes, job_id)
        media_type = "application/pdf"
        filename = f"{job_id}.pdf"
    else:
        raise HTTPException(status_code=400, detail="format 僅支援 docx 或 pdf")

    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/meetings/{meeting_id}")
async def export_kept_meeting(
    meeting_id: str, format: str = "docx", user: CurrentUser = Depends(get_current_user)
):
    """匯出已保留的會議紀錄（依 meeting_id）。format 支援 docx / pdf。"""
    item = db.get_meeting(user_id=user.email, meeting_id=meeting_id)
    if item is None:
        raise HTTPException(status_code=404, detail="找不到此會議紀錄")

    minutes = json.loads(item["minutes_json"])
    title = item["title"]

    if format == "docx":
        content = _build_docx(minutes, title)
        media_type = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        filename = f"{meeting_id}.docx"
    elif format == "pdf":
        content = _build_pdf(minutes, title)
        media_type = "application/pdf"
        filename = f"{meeting_id}.pdf"
    else:
        raise HTTPException(status_code=400, detail="format 僅支援 docx 或 pdf")

    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
