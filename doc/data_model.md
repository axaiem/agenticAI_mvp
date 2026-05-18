# Data Models

To ensure rigorous data quality and improve efficiency when interacting with the LLM for both input structuring and output parsing, we will use **Pydantic**.

Below are the core schema definitions that represent the data boundaries between the system components and the LLM.

## 1. Perception Outputs

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class Observation(BaseModel):
    """The output of the Perception layer based on the current state."""
    goals: List[str] = Field(..., description="The current goals identified from the user query and history.")
    needs_attachment: bool = Field(default=False, description="True if the current goal requires fetching raw artifact bytes.")
    attachment_query: Optional[str] = Field(default=None, description="The specific query or identifier to fetch from Artifacts, if needed.")
```

## 2. Decision Outputs

```python
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict

class ToolCallRequest(BaseModel):
    """Details of a tool invocation requested by the Decision layer."""
    tool_name: str = Field(..., description="The name of the user-defined MCP tool to execute.")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="The arguments required for the tool.")

class DecisionOutput(BaseModel):
    """The definitive output from the Decision layer. Must contain exactly one of answer or tool_call."""
    answer: Optional[str] = Field(default=None, description="Direct plain text answer to the user. Mutually exclusive with tool_call.")
    tool_call: Optional[ToolCallRequest] = Field(default=None, description="A request to execute a specific tool. Mutually exclusive with answer.")
```

## 3. Memory Structures

```python
from pydantic import BaseModel, Field

class MemoryHit(BaseModel):
    """A single relevant memory item retrieved by the Memory layer."""
    handle: str = Field(..., description="A unique identifier/handle for the memory record.")
    descriptor: str = Field(..., description="A textual description summarizing the memory content.")
```
