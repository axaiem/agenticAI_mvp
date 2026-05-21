import json
from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from src.llmgateway import GatewayService, GatewayRequest, TaskComplexity

from src.schemas import Goal, GoalStatus, Hit, Observation

class Perception:
    def __init__(self, gateway: GatewayService):
        self.gateway = gateway
        self.system_prompt = """
        You are the Perception module of an autonomous agent. 
        Analyze the original user query, relevant memory hits, current session history, and prior goals.
        
        Your task is to break down the user query into logical, atomic sub-goals and manage their execution.
        
        Follow these instructions:
        1. DECOMPOSE: Break down the user query into a logical sequence of atomic, actionable goals.
           An atomic goal should represent a single discrete action (e.g., "Search the web for X", "Read file Y", "Extract concept Z", "Synthesize findings").
           - Example A (Research): "Understand the ITR process" -> Goal 1: Search for ITR guidelines, Goal 2: Identify required documents, Goal 3: Synthesize findings.
           - Example B (Action): "Fetch <URL> and find X" -> Goal 1: Read URL, Goal 2: Extract X. (No summary needed if extracting is the final intent).
           Only include a 'Synthesize' or 'Summarize' goal if the task requires compiling complex information from multiple steps to form a final answer. For simple or direct actions, the final action itself is sufficient.
           Never bundle multiple distinct actions into a single goal.
        2. EVALUATE: Check the progress of 'prior goals' against the current 'history'. Update their status (e.g., mark as 'achieved' if completed).
        3. ADD: Append any newly identified atomic goals to the overall goal list. Do not add new goals if a pending prior goal already covers the required action.
        4. SELECT: Choose the single, most immediate 'current_goal' for the agent to execute next from the pending goals.
        5. ATTACH: If the 'current_goal' requires reading raw contents of a specific file/artifact mentioned in the hits, set 'attachment_needed' to true.
        
        You must respond strictly in JSON format matching the provided schema.
        """

    async def observe(
        self, 
        query: str, 
        hits: List[Hit], 
        history: List[Dict[str, Any]], 
        prior_goals: List[Goal]
    ) -> Observation:
        
        # Format the prompt with the current context
        hits_str = json.dumps([hit.model_dump() for hit in hits])
        history_str = json.dumps(history)
        prior_goals_str = json.dumps([goal.model_dump() for goal in prior_goals])
        
        context_prompt = (
            f"{self.system_prompt}\n\n"
            f"Query: {query}\n"
            f"Hits: {hits_str}\n"
            f"History: {history_str}\n"
            f"Prior Goals: {prior_goals_str}"
        )
        
        # Enforce structured output via the LLM Gateway
        request = GatewayRequest(
            user_id="agent6_perception",
            prompt=context_prompt,
            task_complexity=TaskComplexity.MEDIUM, # Maps to 'balanced' capability
            response_format=Observation.model_json_schema()
        )
        
        raw_response = await self.gateway.generate_response(request)
        
        # Parse and adapt the enforced JSON response using Pydantic
        try:
            # Clean potential markdown JSON wrapping from the LLM
            cleaned_response = raw_response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            elif cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
                
            cleaned_response = cleaned_response.strip()
            
            # Use Pydantic to natively parse, coerce, and validate the JSON string
            return Observation.model_validate_json(cleaned_response)
        except Exception as e:
            print(f"Failed to parse perception output: {raw_response}\nError: {e}")
            # Fallback
            return Observation(all_goals=prior_goals, current_goal=None, attachment_needed=False)
