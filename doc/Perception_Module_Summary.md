---

## 2. Initial Design (Designing The Perception Role)
- **Goal**: Introduce a **Perception** component that receives a user query, prior goals, memory hits, and interaction history, then produces a structured `Observation` object via the LLM Gateway.
- **Data Model** (initial Pydantic schemas):
  - `GoalStatus` (enum): `pending`, `in_progress`, `achieved`, `failed`.
  - `Goal`: `id`, `description`, `status`.
  - `Observation`: `all_goals`, `current_goal`, `attachment_needed`.
- **Implementation Highlights**:
  - Added strict `response_format` enforcement in `llmgateway.py` to guarantee JSON output.
  - Integrated the schemas into `src/perception.py`.
  - Provided a **walkthrough.md** artifact with diffs and reasoning.

---

## 3. Prompt Refinement (Refining Agentic Perception Prompt)
### 3.1 First Prompt
```text
1. DECOMPOSE: Break down complex queries into a sequence of atomic, actionable goals.
   - Example: Fetch URL → Extract birth date → Extract death date → Extract contributions.
```
**Result** – Test suite produced correct goal decomposition for the Wikipedia‑fetch example.

### 3.2 Second Prompt (Generalisation)
```text
1. DECOMPOSE: Break down the user query into logical atomic actions.
   - Think like a well‑informed human planner.
   - Example A (Research): Search → Identify docs → Summarise.
   - Example B (Extraction): Read URL → Extract X → Extract Y.
```
**Result** – The module handled a non‑fetch query (ITR filing process) and produced three sensible goals.

### 3.3 Final Prompt (Flexibility & Synthesis Guidance)
```text
1. DECOMPOSE: Break down the query into discrete atomic actions (Search, Read, Extract, Synthesize, etc.).
   - Only add a **Synthesize** goal when the task truly requires integrating multiple results.
   - Do NOT force synthesis for simple extraction or calculation tasks.
```
**Result** – The model now decides when a synthesis step is appropriate, as shown in the discussion about prime‑number calculation vs. multi‑source research.

---

## 4. Test‑Driven Validation
| Test | Scenario | Expected Goals | LLM Model | Outcome |
|------|----------|----------------|-----------|---------|
| `test_perception_initial_query` | ITR filing process | 3 goals (search, identify docs, summarise) | `groq‑llama‑70b` | ✅ Passed – correct decomposition |
| `test_perception_second_iteration` | Prime numbers & product | Goal 1 achieved, Goal 2 pending | `groq‑llama‑70b` | ✅ Passed – state transition works |
| Real LLM run (value of 1 + 1) | Simple arithmetic | Single goal “Calculate 1+1” | `groq‑llama‑70b` | ✅ Passed – clean JSON output |
| Edge case (Wikipedia fetch) | Fetch Claude Shannon info | 4 atomic goals (fetch, birth, death, contributions) | `groq‑llama‑70b` | ✅ Passed – prompt correctly generalises |

**Key observations**
- LiteLLM warnings about optional AWS modules were silenced by setting `LITELLM_LOG="ERROR"` and `SUPPRESS_LITELLM_LOGS="True"`.
- Using `Observation.model_validate_json()` eliminates manual `json.loads()` parsing and automatically coerces minor format issues (e.g., quoted booleans).

---

## 5. Project Re‑organisation (Late‑stage Refactor)
| Action | Before | After |
|--------|--------|-------|
| Move core logic | Root directory (`llmgateway.py`, `perception.py`) | `src/` folder (`src/llmgateway.py`, `src/perception.py`) |
| Tests location | Root (`test_perception.py`, `test_memory.py`, `test.py`) | `tests/` folder (`tests/test_perception.py`, `tests/test_memory.py`, `tests/test_llmgateway.py`) |
| Config JSON | Root (`models_config.json`, `rate_limits.json`) | `config/` folder (`config/models_config.json`, `config/rate_limits.json`) |
| Updated imports | `import llmgateway` | `from src.llmgateway import …` |
| Adjusted file paths in code | Hard‑coded relative paths | Dynamic `os.path.join(Path(__file__).parent.parent, "config", …)` |

All imports and path references were verified with `uv run tests/...` – **all tests pass**.

---

## 6. Final Recommendations & Open Questions
> **Synthesis Goal Guidance** – The current prompt correctly makes synthesis optional. Keep the rule:
> - *Add a “Synthesize & Respond” goal only when the task requires integrating multiple independent pieces of information.*
>
# Perception Module – Design Decision Document

---

## 1. Purpose
The Perception component is the entry point of the **agenticAI_mvp** system. Its responsibility is to translate a user query into a structured, atomic set of goals that downstream modules (Memory, Decision, Action) can act upon. This document records the design decisions, the reasoning behind them, and the advantages they provide.

---

## 2. Core Design Decisions

### 2.1 Goal Representation
- **Decision**: Use a Pydantic model `Goal` with fields `id`, `description`, `status` (enum: pending, in_progress, achieved, failed).
- **Reasoning**: Provides type‑safety, easy validation, and a single source of truth for goal state across the whole application.
- **Advantages**: Guarantees consistent serialization, simplifies debugging, and enables downstream modules to rely on a stable schema.

### 2.2 Observation Schema
- **Decision**: Centralize the `Observation` model (list of all goals, current goal, `attachment_needed` flag) in `src/schemas.py`.
- **Reasoning**: Decouples data contracts from module implementation, allowing multiple agents to share the same schema.
- **Advantages**: Reduces duplication, makes future extensions (e.g., confidence scores, timestamps) straightforward.

### 2.3 Prompt Engineering
- **Decision**: Prompt the LLM to *decompose* any query into atomic actions using a “well‑informed human planner” style.
- **Reasoning**: Empirical tests showed that guiding the model with explicit decomposition rules yields reliable, granular goals.
- **Advantages**: Improves clarity of the generated plan, avoids over‑bundling, and enables the system to handle a wide variety of tasks (research, extraction, calculation).

### 2.4 Optional Synthesis Goal
- **Decision**: Make the “Synthesize & Respond” goal optional; generate it only when a task requires integration of multiple independent results.
- **Reasoning**: For single‑step extraction or calculation a synthesis step adds unnecessary latency.
- **Advantages**: Keeps the agent efficient and reduces token usage, while still supporting complex multi‑source queries when needed.

---

## 3. Prompt Evolution (Rationale)
| Version | Change | Reason |
|---|---|---|
| v1 – Simple fetch | Only instructed to fetch data. | Too narrow; failed on non‑fetch tasks. |
| v2 – Generalised decomposition | Added atomic goal rules, example for research and extraction. | Covered broader task categories. |
| v3 – Human‑planner style | Emphasised “think like a well‑informed planner”, added examples for research and extraction. | Produced more natural, adaptable plans. |
| v4 – Optional synthesis | Added conditional synthesis guidance. | Prevented unnecessary final steps. |

The final prompt (v4) balances flexibility with discipline, ensuring the model always produces a clear goal list and only adds synthesis when justified.

---

## 4. Testing Strategy
- **Unit Tests**: `tests/test_perception.py` covers initial query, second‑iteration, and real‑LLM execution.
- **Scenarios**: Research‑oriented (ITR filing), calculation (prime numbers), and data‑fetching (Wikipedia biography).
- **Validation**: Uses `Observation.model_validate_json` to coerce LLM output into the schema, guaranteeing structural correctness.

---

## 5. Project Re‑organization
- **src/** – core logic (`perception.py`, `schemas.py`, `llmgateway.py`).
- **tests/** – all test files (`test_perception.py`, `test_llmgateway.py`).
- **config/** – JSON configuration (`models_config.json`, `rate_limits.json`).
- Updated import paths and environment variables to reflect the new layout.

---

## 6. Advantages Over Prior Approaches
1. **Strong typing** – Pydantic eliminates runtime parsing errors.
2. **Prompt clarity** – Explicit decomposition yields predictable, granular goals.
3. **Modular schema** – Centralized models simplify cross‑module contracts.
4. **Efficiency** – Optional synthesis reduces unnecessary LLM calls.
5. **Scalable testing** – Real‑LLM and mock tests ensure robustness before deployment.

---

## 7. Open Questions & Future Work
- **Domain‑specific heuristics**: Should we embed specialized prompt sections for legal, scientific, or medical domains?
- **Observation enrichment**: Adding fields like `model_confidence`, `timestamp`, or `source_url` for richer downstream reasoning.
- **Dynamic prompt selection**: Mechanism to choose between prompt variants based on detected task type.

---

*Prepared by Antigravity – your AI coding partner.*
