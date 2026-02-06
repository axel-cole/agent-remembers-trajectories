from pydantic import BaseModel
from typing import Optional, Any, Dict


class Task(BaseModel):
    objective: str
    start_url: str


class AgentRequest(BaseModel):
    task: Task
    is_public: bool = True


class AgentResponse(BaseModel):
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    workflow_id: str
    run_id: str
