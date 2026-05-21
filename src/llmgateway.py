import asyncio
import json
import os
import time
import warnings
from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel
import os
os.environ["LITELLM_LOG"] = "ERROR"
os.environ["SUPPRESS_LITELLM_LOGS"] = "True"

import litellm
litellm.suppress_debug_info = True

from filelock import FileLock
import logging

# Suppress Pydantic serializer warnings commonly raised by LiteLLM response parsing
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

CONFIG_FILE = "config/models_config.json"
LIMITS_FILE = "config/rate_limits.json"
LIMITS_LOCK = "config/rate_limits.json.lock"



class TaskComplexity(str, Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"

class ModelCapability(str, Enum):
    FAST = "fast"
    BALANCED = "balanced"
    CAPABLE = "capable"

class GatewayRequest(BaseModel):
    user_id: str
    prompt: str
    task_complexity: TaskComplexity
    forced_model: Optional[str] = None
    max_tokens: Optional[int] = None
    response_format: Optional[dict] = None

class ModelConfig(BaseModel):
    model_name: str
    base_url: Optional[str] = None
    capability: ModelCapability
    env_key_name: str
    rpm_limit: int
    rpd_limit: int



class RateLimiter:
    def __init__(self):
        if not os.path.exists(LIMITS_FILE):
            with open(LIMITS_FILE, "w") as f:
                json.dump({}, f)
                
    def _read_limits(self) -> dict:
        try:
            with open(LIMITS_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
            
    def _write_limits(self, data: dict):
        with open(LIMITS_FILE, "w") as f:
            json.dump(data, f, indent=2)
            
    def check_and_record(self, model_name: str, config: ModelConfig) -> bool:
        """
        Checks if the model has capacity. If yes, records the request and returns True.
        If no, returns False. Uses FileLock for concurrency safety.
        """
        with FileLock(LIMITS_LOCK):
            data = self._read_limits()
            now_ts = time.time()
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
            if model_name not in data:
                data[model_name] = {
                    "last_request_time": 0.0,
                    "minute_timestamps": [],
                    "today_date": today_str,
                    "calls_today": 0
                }
                
            model_data = data[model_name]
            
            # Reset daily count if it's a new day
            if model_data.get("today_date") != today_str:
                model_data["calls_today"] = 0
                model_data["today_date"] = today_str
                
            # Clean up minute timestamps
            recent_timestamps = [ts for ts in model_data.get("minute_timestamps", []) if now_ts - ts < 60]
            model_data["minute_timestamps"] = recent_timestamps
            
            # Check limits
            if len(recent_timestamps) >= config.rpm_limit:
                return False
            if model_data["calls_today"] >= config.rpd_limit:
                return False
                
            # Record the new request
            model_data["minute_timestamps"].append(now_ts)
            model_data["calls_today"] += 1
            model_data["last_request_time"] = now_ts
            
            self._write_limits(data)
            return True

class ModelRouter:
    def __init__(self):
        with open(CONFIG_FILE, "r") as f:
            raw_config = json.load(f)
            self.models: Dict[str, ModelConfig] = {
                k: ModelConfig(**v) for k, v in raw_config.items()
            }
            
        self.complexity_mapping = {
            TaskComplexity.SIMPLE: ModelCapability.FAST,
            TaskComplexity.MEDIUM: ModelCapability.BALANCED,
            TaskComplexity.COMPLEX: ModelCapability.CAPABLE
        }
        
    def select_model(self, request: GatewayRequest, rate_limiter: RateLimiter) -> str:
        # 1. Check Forced Model
        if request.forced_model:
            if request.forced_model not in self.models:
                raise ValueError(f"Forced model {request.forced_model} not in config.")
            config = self.models[request.forced_model]
            if rate_limiter.check_and_record(request.forced_model, config):
                return request.forced_model
            else:
                raise Exception(f"Forced model {request.forced_model} is rate limited.")

        # 2. Dynamic Routing
        target_cap = self.complexity_mapping[request.task_complexity]
        
        # Build list of fallback capabilities
        caps_to_try = [target_cap]
        if target_cap == ModelCapability.CAPABLE:
            caps_to_try.extend([ModelCapability.BALANCED, ModelCapability.FAST])
        elif target_cap == ModelCapability.BALANCED:
            caps_to_try.append(ModelCapability.FAST)
            
        for cap in caps_to_try:
            # Get all models matching this capability
            eligible_models = [name for name, cfg in self.models.items() if cfg.capability == cap]
            for m_name in eligible_models:
                if rate_limiter.check_and_record(m_name, self.models[m_name]):
                    if cap != target_cap:
                        print(f"⚠️ Primary capability exhausted. Falling back to {m_name}")
                    return m_name
                    
        raise Exception("Rate limit exceeded across all available models.")
        
    def get_model_config(self, model_name: str) -> ModelConfig:
        return self.models[model_name]

class GatewayService:
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.router = ModelRouter()
        
    async def generate_response(self, request: GatewayRequest, mock_execution=False) -> str:
        try:
            model_name = self.router.select_model(request, self.rate_limiter)
            config = self.router.get_model_config(model_name)
            print(f"[{request.user_id}] Selected Model: {model_name} ({config.model_name})")
            
            if mock_execution:
                await asyncio.sleep(0.1)
                return f"Mock response from {config.model_name}"
                
            # litellm will automatically pick up the env var specified, but we could also inject it if needed
            # e.g., os.environ.get(config.env_key_name)
            
            completion_kwargs = {
                "model": config.model_name,
                "messages": [{"role": "user", "content": request.prompt}],
                "max_tokens": request.max_tokens,
                "api_key": os.environ.get(config.env_key_name),
                "api_base": config.base_url
            }
            if request.response_format:
                completion_kwargs["response_format"] = {"type": "json_schema", "json_schema": {"name": "response", "schema": request.response_format, "strict": True}}

            response = await litellm.acompletion(**completion_kwargs)
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"[{request.user_id}] Gateway failed: {str(e)}")
            return "Error during LLM execution."

async def run_simulation():
    print("--- Starting JSON-backed LLM Gateway Simulation ---")
    
    # Clear old rate limits for clean test
    if os.path.exists(LIMITS_FILE):
        os.remove(LIMITS_FILE)
        
    gateway = GatewayService()
    
    print("\n1. Standard Dynamic Routing Test")
    req1 = GatewayRequest(user_id="u1", prompt="test", task_complexity=TaskComplexity.COMPLEX)
    await gateway.generate_response(req1, mock_execution=True)
    
    print("\n2. Forced Model Test")
    req2 = GatewayRequest(user_id="u2", prompt="test", task_complexity=TaskComplexity.SIMPLE, forced_model="openrouter-claude-sonnet")
    await gateway.generate_response(req2, mock_execution=True)
    
    print("\n3. Rate Limit Fallback Test (Spamming Capable tier)")
    # openrouter-claude-sonnet has limit of 2. Total 2.
    for i in range(3):
        await gateway.generate_response(req1, mock_execution=True)
        
if __name__ == "__main__":
    asyncio.run(run_simulation())
