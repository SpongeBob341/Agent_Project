# Agent Architecture and Implementation Details

This document provides a detailed walkthrough of the agent's architecture, its problem-solving methodology, and points to the key implementation details in the codebase.

## 1. High-Level Agent Workflow

The agent employs a multi-layered, dynamic strategy to solve a given problem. The core philosophy is to first plan, then execute multiple reasoning strategies in parallel to foster self-consistency, and finally, aggregate the results to find a consensus answer. If no consensus is reached, it triggers a self-correction mechanism as a final attempt.

The workflow can be summarized in four main stages, orchestrated by the `solve` method in `core.py`:

1.  **Analyze & Plan**: The agent first deconstructs the problem to understand its nature and create a high-level plan.
2.  **Execute Strategies with Self-Consistency**: Based on the plan, the agent runs a mix of different reasoning strategies (like Chain-of-Thought, Program-Aided Language Models, and ReAct) to generate a diverse set of potential answers.
3.  **Aggregate Answers**: The agent collects the answers from the different strategies and performs a majority vote to find the most reliable one.
4.  **Fallback & Self-Correct**: If the aggregation stage fails to produce a confident answer, the agent enters a self-correction mode, analyzing the previous failed attempts to make a final, more informed guess.

---

## 2. Detailed Implementation Breakdown

### 2.1. Stage 1: Analyze & Plan

This initial stage is crucial for guiding the subsequent steps.

-   **Function**: `Agent.plan(question)` in `core.py`
-   **Prompt**: `PLANNER_PROMPT` in `prompts.py`
-   **Description**: When the `solve` method is called, it first invokes `make_plan`. This method sends the user's question to the LLM using the `PLANNER_PROMPT`. The LLM's task is to analyze the question and return three key pieces of information:
    -   `PROBLEM_TYPE`: A classification of the problem (e.g., `Math`, `Logic`, `Common Sense`).
    -   `PLAN`: A natural language, step-by-step plan to solve the problem.
    -   `STRATEGY_RECOMMENDATION`: A suggestion to either `Use Python` (for calculation-heavy tasks) or `Use Reasoning` (for logic or knowledge-based tasks).
-   **Parsing**: The output from the planner is parsed by the `Agent.parse_plan(plan_text)` function in `core.py`, which uses regular expressions to extract these three fields.

### 2.2. Stage 2: Execute Strategies

This is the core reasoning phase. Instead of relying on a single technique, the agent implements a **self-consistency** approach by running multiple strategies. The choice of strategies is determined by the `STRATEGY_RECOMMENDATION` from the planning stage.

-   **Function**: `Agent.solve(question)` in `core.py`
-   **Description**: Inside the `solve` method, a `strategies_to_run` list is created.
    -   If the recommendation is "Python", the list becomes `["Python", "Python", "CoT"]`. This prioritizes code-based solutions, which are generally more accurate for math, but includes a reasoning-based approach as a backup.
    -   If the recommendation is "Reasoning", the list becomes `["CoT", "CoT", "ReAct"]`, focusing on different reasoning-based methods.
-   The agent then iterates through this list, calling `Agent.execute_strategy` for each one.

The following strategies are implemented:

#### A. Program-Aided Language Model (PAL) - The "Python" Strategy

This strategy offloads calculation and symbolic math to a Python interpreter.

-   **Function**: `Agent.solve_pal(question, plan)` in `core.py`
-   **Prompt**: `PAL_PROMPT` in `prompts.py`
-   **Tool**: `execute_python(code)` in `tools.py`
-   **Description**:
    1.  `solve_pal` is called, which formats the `PAL_PROMPT` with the question and the plan.
    2.  The LLM is asked to generate a Python script to solve the problem.
    3.  The generated code is extracted from the LLM's response.
    4.  The code is then executed using the `execute_python` tool. This tool is a critical component, as it runs the code in a **separate, sandboxed process** with a timeout. This prevents infinite loops and restricts access to sensitive system functions, making code execution safe. The sandboxing is configured in the `_exec_worker` function in `tools.py`, which explicitly defines a `safe_globals` dictionary of allowed modules and functions.
    5.  **Error Correction Loop**: If the code execution fails, `solve_pal` does not give up. It enters a loop (for up to 2 retries) where it uses the `PAL_ERROR_CORRECTION_PROMPT` from `prompts.py`. This prompt provides the LLM with the original code and the resulting error message, asking it to provide a fix. The corrected code is then executed again.

#### B. Chain-of-Thought (CoT) - The "Reasoning" Strategy

This is the primary strategy for problems requiring logical deduction or general knowledge.

-   **Function**: `Agent.type_cot(question, plan, problem_type)` in `core.py`
-   **Prompt**: `COT_PROMPT` in `prompts.py`
-   **Description**:
    1.  `solve_cot` uses the `COT_PROMPT` to ask the LLM to "think step by step" and provide a detailed reasoning process before giving the final answer.
    2.  **Self-Fact-Checking**: For problems identified as "Common Sense" or "Logic", the agent adds a layer of verification. After generating an initial answer, it calls the LLM again using the `COT_FACT_CHECK_PROMPT` from `prompts.py`. This prompt asks the LLM to act as a strict reviewer, double-check its own work for flaws, and provide a corrected answer if any are found. This improves the reliability of the final output.

#### C. ReAct (Reason + Act)

This is a more complex, stateful strategy where the agent can iteratively use tools to find an answer.

-   **Function**: `Agent.type_react(question)` in `core.py`
-   **Prompt**: `REACT_PROMPT` in `prompts.py`
-   **Description**:
    1.  `solve_react` initiates a loop that can run for a maximum of 7 steps.
    2.  The agent maintains a `history` of the conversation, which starts with the `REACT_PROMPT`.
    3.  In each step, the LLM is prompted to produce a `Thought` and an `Action`. The only available action is `Python Code`.
    4.  If the LLM decides to use the tool, the agent extracts the Python code block and executes it using the same safe `execute_python` tool.
    5.  The result of the code execution (the `Observation`) is then appended to the history and fed back to the LLM in the next step, allowing it to course-correct or continue its reasoning.
    6.  **Context Management**: Since the history can grow very long in a ReAct loop, a summarization mechanism is implemented in `Agent._summarize_history`. If the conversation history exceeds a certain token threshold, it uses the `SUMMARIZE_HISTORY_PROMPT` to ask the LLM to create a concise summary of the intermediate steps, which then replaces the detailed history to save context space.

### 2.3. Stage 3: Aggregate Answers

After executing the chosen strategies, the agent may have multiple, potentially different, answers.

-   **Function**: `Agent.aggregate_answers(answers)` in `core.py`
-   **Description**:
    1.  This function takes the list of cleaned answers from the execution stage.
    2.  It first normalizes the answers using the `Agent.normalize` helper function to ensure consistent formatting (e.g., "8.0" becomes "8").
    3.  It then uses `collections.Counter` to count the occurrences of each unique answer.
    4.  If any answer appears at least once (a relaxed majority), it is chosen as the consensus answer.

### 2.4. Stage 4: Fallback & Self-Correct

If the aggregation stage does not yield a majority answer (e.g., all three strategies produced a different answer, or all failed), the agent makes one final attempt.

-   **Function**: `Agent.auto_correct(question, previous_answers)` in `core.py`
-   **Prompt**: `SELF_CORRECTION_PROMPT` in `prompts.py`
-   **Description**:
    1.  The `solve` method calls `self_correct` if `aggregate_answers` returns `None`.
    2.  This function uses the `SELF_CORRECTION_PROMPT`, providing the LLM with the original question and the list of previously generated (and presumably incorrect) answers.
    3.  The LLM is asked to analyze why the previous attempts might have failed and to try solving the problem again from a new perspective. This serves as a powerful fallback mechanism.

---

## 3. Supporting Components

-   **LLM Client** (`llm_client.py`): The `LLMClient` class is a simple wrapper around the `requests` library to handle all communication with the OpenAI-style API. It is used by all agent components that need to query the LLM.
-   **Answer Extraction** (`core.py`): The `Agent.extract_final(text)` function is a vital utility. LLM outputs are often verbose. This function uses a series of regular expressions and fallbacks to robustly extract the final answer from the raw text, looking for patterns like `Final Answer: ...`, `\boxed{...}`, or simply taking the last line of a short response. This ensures that the agent works with clean, consistent data in the aggregation stage.

## AI Usage Acknowledgement
This project abides by the course policy regarding AI tools. 
I used Google Gemini as a conceptual thought partner during development.

**Specific usages:**
* **Conceptual Understanding:** Asked for explanations of "Self-Consistency" and "Reflexion" algorithms.
* **Debugging:** Used AI to interpret error codes and understand how to handle JSON parsing exceptions.

**Statement of Originality:** All code submitted in this repository was written by me. Where AI provided code snippets for explanation, I rewrote the logic manually to fit my specific architecture and constraints.
