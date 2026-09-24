from pydantic import BaseModel
from enum import IntEnum
from typing import Optional


class Stage(IntEnum):
    SANDBOXED = 0
    FILE_ACCESS = 1
    WEB_ACCESS = 2
    CODE_EXECUTION = 3
    HUGGINGFACE_MOMENT = 4


STAGE_META = {
    Stage.SANDBOXED: {
        "name": "Sandboxed",
        "description": "Chat only. No tools, no access.",
        "tools": [],
        "risk_label": "Minimal",
    },
    Stage.FILE_ACCESS: {
        "name": "File Access",
        "description": "Agent can read and write files via MCP.",
        "tools": ["read_file", "write_file", "list_directory"],
        "risk_label": "Low",
    },
    Stage.WEB_ACCESS: {
        "name": "Web + File Access",
        "description": "Agent can make HTTP requests and access files.",
        "tools": ["read_file", "write_file", "list_directory", "http_get", "http_post"],
        "risk_label": "Medium",
    },
    Stage.CODE_EXECUTION: {
        "name": "Full Access",
        "description": "Agent can execute arbitrary code, access files, and the web.",
        "tools": [
            "read_file", "write_file", "list_directory",
            "http_get", "http_post",
            "execute_code", "run_shell",
        ],
        "risk_label": "Critical",
    },
    Stage.HUGGINGFACE_MOMENT: {
        "name": "The Guardrails Paradox",
        "description": "When safety mechanisms become the vulnerability.",
        "tools": [],
        "risk_label": "Systemic",
    },
}


class ChatMessage(BaseModel):
    role: str
    content: str
    tool_call: Optional[str] = None
    tool_result: Optional[str] = None
    risk_level: Optional[str] = None


class TraceSpan(BaseModel):
    id: str
    name: str
    tool: Optional[str] = None
    parameters: Optional[dict] = None
    result: Optional[str] = None
    duration_ms: float
    risk_level: str = "safe"
    children: list["TraceSpan"] = []
    timestamp: Optional[str] = None


class RedTeamResult(BaseModel):
    attack_type: str
    prompt: str
    agent_response: str
    tool_calls: list[TraceSpan]
    risk_score: float
    verdict: str
    explanation: str


class StageState(BaseModel):
    stage: int = 0
    risk_score: float = 0.0
    tools_granted: list[str] = []
    conversation: list[ChatMessage] = []
    traces: list[TraceSpan] = []
    red_team_results: list[RedTeamResult] = []
