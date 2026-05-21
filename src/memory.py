import os
import json
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from src.llmgateway import GatewayService, GatewayRequest, TaskComplexity
from src.schemas import Hit, MemoryRecord

class MemoryRetrievalResponse(BaseModel):
    selected_handles: List[str] = Field(description="List of handles of memory records relevant to the current user query and history.")

class Memory:
    def __init__(self, filepath: str, gateway: GatewayService):
        self.filepath = filepath
        self.gateway = gateway
        self._ensure_seeded()

    def _ensure_seeded(self):
        """If the memory file doesn't exist, seed it with default workspace docs."""
        if not os.path.exists(self.filepath):
            default_records = []
            # Known files in the workspace
            known_docs = {
                "doc/requirements.md": "Product requirements and capabilities for agent6.py autonomous loop.",
                "doc/architecture.md": "Architecture design and interaction flow diagrams for agent6.py components.",
                "doc/data_model.md": "Core Pydantic data schemas representing component boundaries."
            }
            
            for path, desc in known_docs.items():
                # We can check if file exists, or just seed it as reference
                # If file exists, read its contents
                content = None
                if os.path.exists(path):
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            content = f.read()
                    except Exception:
                        pass
                
                default_records.append(
                    MemoryRecord(
                        handle=path,
                        descriptor=desc,
                        content=content,
                        timestamp=time.time()
                    )
                )
            
            self.save_memory(default_records)

    def load_memory(self) -> List[MemoryRecord]:
        if not os.path.exists(self.filepath):
            return []
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [MemoryRecord.model_validate(item) for item in data]
        except Exception as e:
            print(f"Error loading memory from {self.filepath}: {e}")
            return []

    def save_memory(self, records: List[MemoryRecord]) -> None:
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump([rec.model_dump() for rec in records], f, indent=2)
        except Exception as e:
            print(f"Error saving memory to {self.filepath}: {e}")

    async def read(self, query: str, history: List[Dict[str, Any]]) -> List[Hit]:
        records = self.load_memory()
        if not records:
            return []

        # Prepare candidates for the LLM to select from
        candidates = [
            {"handle": rec.handle, "descriptor": rec.descriptor}
            for rec in records
        ]

        system_prompt = """
        You are the Retrieval component of an autonomous agent's Memory module.
        Your job is to select which stored memories (documents or past execution outcomes) are relevant to the user's current query and conversation history.

        You are provided with:
        1. The current user query.
        2. The conversation history.
        3. A list of candidate memory records, each with a 'handle' and a 'descriptor'.

        Choose only the records that are highly relevant to answering the query or understanding the current context. Return a JSON object with 'selected_handles' containing the list of relevant handles. If none are relevant, return an empty list.
        """

        context_prompt = (
            f"{system_prompt}\n\n"
            f"Query: {query}\n"
            f"History: {json.dumps(history)}\n"
            f"Candidates: {json.dumps(candidates)}"
        )

        request = GatewayRequest(
            user_id="agent6_memory_retrieval",
            prompt=context_prompt,
            task_complexity=TaskComplexity.SIMPLE,
            response_format=MemoryRetrievalResponse.model_json_schema()
        )

        try:
            raw_response = await self.gateway.generate_response(request)
            
            # Clean possible markdown JSON wrappers
            cleaned = raw_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            parsed = MemoryRetrievalResponse.model_validate_json(cleaned)
            selected_set = set(parsed.selected_handles)

            # Map selected handles back to Hit objects
            hits = []
            for rec in records:
                if rec.handle in selected_set:
                    hits.append(Hit(handle=rec.handle, descriptor=rec.descriptor))
            return hits

        except Exception as e:
            print(f"Memory retrieval failed: {e}. Falling back to simple keyword matching.")
            # Fallback keyword matching
            hits = []
            query_lower = query.lower()
            for rec in records:
                if rec.handle.lower() in query_lower or any(word in rec.descriptor.lower() for word in query_lower.split()):
                    hits.append(Hit(handle=rec.handle, descriptor=rec.descriptor))
            return hits

    def record_outcome(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any], 
        result: str, 
        artifact_id: Optional[str] = None
    ) -> None:
        records = self.load_memory()
        
        # Determine the handle
        handle = artifact_id if artifact_id else f"outcome_{int(time.time())}"
        
        # Build descriptor
        result_preview = result[:150] + "..." if len(result) > 150 else result
        descriptor = f"Result of executing tool '{tool_name}' with args {json.dumps(arguments)}: {result_preview}"
        
        new_record = MemoryRecord(
            handle=handle,
            descriptor=descriptor,
            content=result,
            timestamp=time.time()
        )
        
        records.append(new_record)
        self.save_memory(records)
