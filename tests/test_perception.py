import asyncio
from src.perception import Perception
from src.schemas import Hit, Observation, Goal, GoalStatus
from src.llmgateway import GatewayService

async def test_perception_initial():
    # Using the real GatewayService
    gateway = GatewayService()
    perception = Perception(gateway)
    
    # query = "Why did dose become expensive last month is it inflation or supply chain issues or iran war?"
    query = "Whats the population of india? How has it grown over the last century"
    hits = []
    history = []
    prior_goals = []
    
    print("--- Testing Perception Module: Initial Query ---")
    observation = await perception.observe(query, hits, history, prior_goals)
    
    print(f"\nAll Goals:")
    for g in observation.all_goals:
        print(f"  - [{g.status.value}] {g.id}: {g.description}")
        
    print(f"\nCurrent Goal: {observation.current_goal.id if observation.current_goal else 'None'}")
    print(f"Attachment Needed: {observation.attachment_needed}")
    
    assert len(observation.all_goals) >= 1
    assert observation.current_goal is not None
    print("\nInitial Query Test passed successfully!")

async def test_perception_second_iteration():
    gateway = GatewayService()
    perception = Perception(gateway)
    
    query = "Which are the first two prime number and whats the product of them?"
    
    # Mocking the prior goals as if the perception module had already broken it down in a previous step
    prior_goals = [
        Goal(id="goal_1", description="Identify the first two prime numbers", status=GoalStatus.PENDING),
        Goal(id="goal_2", description="Calculate the product of the first two prime numbers", status=GoalStatus.PENDING)
    ]
    
    # Mocking the history showing that goal_1 has been accomplished
    history = [
        {
            "role": "assistant",
            "content": "I have successfully identified the first two prime numbers. They are 2 and 3."
        }
    ]
    
    hits = [] # Assume no memory hits needed for this simple calculation
    
    print("\n--- Testing Perception Module: Second Iteration ---")
    observation = await perception.observe(query, hits, history, prior_goals)
    
    print(f"\nAll Goals:")
    for g in observation.all_goals:
        print(f"  - [{g.status.value}] {g.id}: {g.description}")
        
    print(f"\nCurrent Goal: {observation.current_goal.id if observation.current_goal else 'None'}")
    print(f"Attachment Needed: {observation.attachment_needed}")
    
    # Assert that goal_1 was marked as achieved based on the history
    goal_1 = next((g for g in observation.all_goals if g.id == "goal_1"), None)
    assert goal_1 is not None and goal_1.status == GoalStatus.ACHIEVED
    
    # Assert that goal_2 is now the current goal
    assert observation.current_goal.id == "goal_2"
    print("\nSecond Iteration Test passed successfully!")

async def main():
    await test_perception_initial()
    await test_perception_second_iteration()

if __name__ == "__main__":
    asyncio.run(main())
