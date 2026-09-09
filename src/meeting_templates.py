from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class MeetingTemplate:
    code: str
    name: str
    # None 代表自由格式（如 general），沿用現行 topics 自由格式行為。
    section_titles: Optional[List[str]]


TEMPLATES: dict[str, MeetingTemplate] = {
    "general": MeetingTemplate(
        code="general",
        name="一般會議",
        section_titles=None,
    ),
    "project_status": MeetingTemplate(
        code="project_status",
        name="專案進度會議",
        section_titles=["進度更新", "風險與阻礙", "下一步計畫"],
    ),
    "client_meeting": MeetingTemplate(
        code="client_meeting",
        name="客戶業務會議",
        section_titles=["客戶需求", "討論重點", "後續跟進"],
    ),
    "brainstorm": MeetingTemplate(
        code="brainstorm",
        name="腦力激盪",
        section_titles=["發想主題", "點子清單", "後續評估"],
    ),
    "retro": MeetingTemplate(
        code="retro",
        name="Retro",
        section_titles=["Keep", "Problem", "Try"],
    ),
}


DEFAULT_TEMPLATE_CODE = "general"


def get_template(code: Optional[str]) -> MeetingTemplate:
    """依代碼取得模板；未帶或為 None 視為預設 general。呼叫端須先確認代碼有效。"""
    resolved = code or DEFAULT_TEMPLATE_CODE
    return TEMPLATES[resolved]


def valid_codes_sorted() -> list[str]:
    return sorted(TEMPLATES.keys())
