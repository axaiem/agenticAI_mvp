# Product Requirements

## Project Goal
Implement an Agentic AI (`agent6.py`) that operates in a continuous loop, delegating tasks across distinct roles for memory retrieval, perception, decision-making, and action execution.

## Key Capabilities & Requirements

1. **Context Retrieval (Memory)**
   - The system must be able to read past history and queries to retrieve relevant context.
   - Memory will be **backed by a JSON file** for simplicity and persistence.
   - Memory should return structured `hits` containing handles and descriptors.
   - The system must be able to record the outcomes of tool executions back into memory.

2. **Goal Parsing & Observation (Perception)**
   - A perception layer must analyze the current query, memory hits, history, and prior goals.
   - It must output a clear `Observation` containing the current goals and indicate if any artifact attachments are necessary.
   - **Data Quality**: The output must be strictly validated using **Pydantic** models to ensure correct formatting from the LLM.
   - **LLM Gateway**: All LLM inference requests made by the perception layer must be routed through the internal LLM Gateway.

3. **Artifact Handling**
   - If the perception layer indicates an attachment is needed, the system must fetch the raw bytes using the `Artifacts` component before proceeding to the decision phase.

4. **Decision Making**
   - The decision engine must take the current goal, memory hits, any attached bytes, history, and available tools to determine the next step.
   - **Pydantic validation** is required to guarantee the LLM outputs exactly one of the two types:
     - **Direct Answer**: A plain text response to the user.
     - **Tool Call**: A structured request to execute a specific tool.
   - **LLM Gateway**: All LLM inference requests made by the decision engine must be routed through the internal LLM Gateway.

5. **Tool Execution (Action / MCP)**
   - When a tool is selected, the system must execute it via the Model Context Protocol (MCP).
   - The agent should be equipped with **User-Defined MCP Tools**, such as:
     - `read_file` / `write_file` for local filesystem interaction.
     - `web_search` for gathering external context.
     - (Other custom tools to be defined based on user needs).
   - The execution must return a descriptor and an optional `artifact_id` which are then logged to memory.

6. **State Management**
   - The orchestrator (`agent6 loop`) must append the results of each iteration to the history and loop until the task is complete.
