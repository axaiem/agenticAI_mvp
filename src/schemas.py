from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional

class GoalStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    ACHIEVED = "achieved"
    FAILED = "failed"

class Goal(BaseModel):
    id: str = Field(description="Unique identifier for the goal")
    description: str = Field(description="Detailed description of the goal")
    status: GoalStatus = Field(description="Current status of the goal")

class Hit(BaseModel):
    handle: str
    descriptor: str

class Observation(BaseModel):
    all_goals: List[Goal] = Field(description="List of all goals, including updated statuses of prior goals and any new goals discovered.")
    current_goal: Optional[Goal] = Field(description="The specific goal that should be focused on in the immediate next step.")
    attachment_needed: bool = Field(description="True if an artifact attachment is required to proceed with the current goal.")

class MemoryRecord(BaseModel):
    handle: str = Field(description="Unique identifier/handle for the memory record (e.g., path or URL)")
    descriptor: str = Field(description="Summary descriptor of what the record contains")
    content: Optional[str] = Field(default=None, description="Raw content of the record if stored directly")
    timestamp: float = Field(description="Epoch timestamp when recorded")

