import asyncio
import os
from dotenv import load_dotenv
from src.llmgateway import GatewayService, GatewayRequest, TaskComplexity

async def run_gateway_call():
    # Load environment variables
    load_dotenv()
    
    gateway = GatewayService()
    
    # Get all configured models from the router
    models = list(gateway.router.models.keys())
    print(f"Discovered configured models: {models}\n")
    
    # Sequentially call each model and output the response
    for model_name in models:
        print(f"\n==================================================")
        print(f"🚀 Calling model: {model_name}...")
        
        request = GatewayRequest(
            user_id="user_batch",
            prompt="Hello, world!",
            task_complexity=TaskComplexity.SIMPLE,
            forced_model=model_name
        )
        
        response = await gateway.generate_response(request, mock_execution=False)
        print(f"\n--- Response from {model_name} ---")
        print(response)
        print(f"==================================================")

def main():
    asyncio.run(run_gateway_call())

if __name__ == "__main__":
    main()
