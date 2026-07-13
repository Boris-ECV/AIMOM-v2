from pydantic import BaseModel
from typing import List, Optional


class UploadResponse(BaseModel):
    job_id: str
    filename: str
    duration_sec: float
    size_bytes: int


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


class SummarizeResponse(BaseModel):
    job_id: str
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
