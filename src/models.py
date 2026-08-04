from pydantic import BaseModel
from typing import List, Optional


class UploadResponse(BaseModel):
    job_id: str
    filename: str
    duration_sec: float
    size_bytes: int


class UploadPresignRequest(BaseModel):
    filename: str


class UploadPresignResponse(BaseModel):
    job_id: str
    upload_url: str
    s3_key: str
    content_type: str


class UploadCompleteRequest(BaseModel):
    job_id: str
    s3_key: str
    filename: str


class Segment(BaseModel):
    start: float
    end: float
    text: str
    speaker: Optional[str] = None


class TranscribeRequest(BaseModel):
    job_id: str


class TranscribeResponse(BaseModel):
    job_id: str
    segments: List[Segment]
    full_text: str


class TranscriptResultResponse(BaseModel):
    """TASK-016：/transcribe 改為非同步後，逐字稿結果改由此端點取得。"""
    job_id: str
    stage: str
    segments: List[Segment]
    full_text: str


class DiarizeRequest(BaseModel):
    job_id: str


class DiarizeResponse(BaseModel):
    job_id: str
    speakers: List[str]
    segments: List[Segment]


class SummarizeRequest(BaseModel):
    job_id: str


class ActionItem(BaseModel):
    owner: str
    task: str
    due: str


class Topic(BaseModel):
    title: str
    content: str


class MeetingInfo(BaseModel):
    """會議基本資訊。逐字稿未提及的欄位一律為空字串／空陣列，
    由前端結果頁面提供手動填寫/修正欄位，AI 不得臆測。"""
    date: str = ""
    time: str = ""
    location: str = ""
    participants: List[str] = []


class SummarizeResponse(BaseModel):
    job_id: str
    meeting_info: MeetingInfo
    summary: str
    action_items: List[ActionItem]
    decisions: List[str]
    topics: List[Topic]


class StatusResponse(BaseModel):
    job_id: str
    stage: str
    progress: int
    message: str


class CleanupResponse(BaseModel):
    deleted: bool
    job_id: str
