import os
import json
import asyncio
from src.memory import Memory
from src.schemas import MemoryRecord, Hit
from src.llmgateway import GatewayService

# Temporary test file path
TEST_MEM_FILE = "test_memory.json"

def cleanup():
    if os.path.exists(TEST_MEM_FILE):
        try:
            os.remove(TEST_MEM_FILE)
        except Exception:
            pass

async def test_memory_seeding():
    cleanup()
    class DummyGateway:
        pass
    
    gateway = DummyGateway()
    # Initializing memory should auto-seed
    memory = Memory(TEST_MEM_FILE, gateway)
    
    assert os.path.exists(TEST_MEM_FILE)
    records = memory.load_memory()
    assert len(records) > 0
    
    handles = [rec.handle for rec in records]
    assert "doc/requirements.md" in handles
    assert "doc/architecture.md" in handles
    assert "doc/data_model.md" in handles
    cleanup()

async def test_record_outcome():
    cleanup()
    class DummyGateway:
        pass
    
    gateway = DummyGateway()
    memory = Memory(TEST_MEM_FILE, gateway)
    
    initial_count = len(memory.load_memory())
    
    # Record a tool execution outcome
    memory.record_outcome(
        tool_name="web_search",
        arguments={"query": "agentic loop"},
        result="Success: Found 3 articles about Agentic AI patterns.",
        artifact_id="search_outcome_1"
    )
    
    records = memory.load_memory()
    assert len(records) == initial_count + 1
    
    new_rec = next(rec for rec in records if rec.handle == "search_outcome_1")
    assert "web_search" in new_rec.descriptor
    assert "Found 3 articles" in new_rec.descriptor
    assert new_rec.content == "Success: Found 3 articles about Agentic AI patterns."
    cleanup()

async def test_memory_read_llm():
    cleanup()
    class MockGateway:
        def __init__(self):
            self.last_request = None
            
        async def generate_response(self, request):
            self.last_request = request
            # Simulate returning json format containing the selected handles
            return '{"selected_handles": ["doc/requirements.md"]}'
            
    mock_gateway = MockGateway()
    memory = Memory(TEST_MEM_FILE, mock_gateway)
    
    hits = await memory.read(
        query="What are the product requirements for agent6?",
        history=[]
    )
    
    # Verify request was sent correctly
    assert mock_gateway.last_request is not None
    assert mock_gateway.last_request.response_format is not None
    
    # Verify we got the correct Hit mapped back
    assert len(hits) == 1
    assert hits[0].handle == "doc/requirements.md"
    assert "requirements" in hits[0].descriptor.lower()
    cleanup()

async def test_memory_read_fallback():
    cleanup()
    class ErrorGateway:
        async def generate_response(self, request):
            raise Exception("Gateway error")
            
    gateway = ErrorGateway()
    memory = Memory(TEST_MEM_FILE, gateway)
    
    # The read call should not fail; it should fallback gracefully
    hits = await memory.read(
        query="architecture",
        history=[]
    )
    
    # Fallback should do keyword matching and find architecture.md
    assert len(hits) >= 1
    assert any(h.handle == "doc/architecture.md" for h in hits)
    cleanup()

async def main():
    print("--- Running test_memory.py manually ---")
    await test_memory_seeding()
    print("Seeding test passed!")
    await test_record_outcome()
    print("Record outcome test passed!")
    await test_memory_read_llm()
    print("LLM read test passed!")
    await test_memory_read_fallback()
    print("Fallback read test passed!")
    print("All tests passed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
