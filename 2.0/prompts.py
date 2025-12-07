PLANNER_PROMPT = """You are an intelligent problem solver.
Your goal is to analyze the given user question and create a step-by-step plan to solve it.

Question: {question}

Analyze the problem and output the following:
PROBLEM_TYPE: [Math/Logic/Common Sense]
PLAN:
1. ...
2. ...
STRATEGY_RECOMMENDATION: [Use Python/Use Reasoning]
"""

PAL_PROMPT = """You are a Python expert. Write a Python script to solve this problem.
The script must calculate the final answer and print it using `print()`.
Do not use input() or other interactive functions.
Use the `math` library for basic math.
Use the `sympy` library for algebra, equation solving, and symbolic math. It is already imported.

Problem: {question}
Plan: {plan}

Code:
```python
"""

COT_PROMPT = """You are an expert in maths, reasoning, planning, common sense, and general knowledge, think step by step.

Problem: {question}
Plan: {plan}

Instructions:
- For Logical/Math problems: Think step-by-step.
- For Common Sense/Factual problems: Think step-by-step, Retrieve knowledge and verify facts.

Special Instruction:
- For writing python code: No reasoning is required just give the code block, no need to follow response structure
- Give final answer in format: Code: <answer> 

Structure your response as follows:
1. Reasoning: Be CONCISE (under 1000 words). Focus only on the necessary steps or facts.
2. Output the result in the format: Final Answer: <answer>

Do not stop until you have printed the "Final Answer:".
"""

REACT_PROMPT = """You are an agent that can think and act.
Your goal is to solve the question.
You have access to a tool:
- Python Executor: Run python code to calculate or simulate.

Use the following format:

Question: the input question
Thought: you should always think about what to do
Action: [Python Code / None]
Action Input: [The python code to run inside ```python ... ```]
Observation: [The result of the code]
(this Thought/Action/Observation can repeat N times)
Thought: I have the final answer
Final Answer: [The final answer]

Question: {question}

IMPORTANT:
- Write CONCISE code.
- Do NOT repeat comments.
- Do NOT loop the same text.
- If you are stuck, try a different approach.
"""

SELF_CORRECTION_PROMPT = """The previous attempts to solve the problem failed or produced inconsistent results.
Problem: {question}

Previous Attempts/Errors:
{attempts}

Analyze why these might have failed.
Then, provide a NEW, BETTER prompt or strategy to solve it.
Finally, try to solve it yourself using that new perspective.
Output the result in the format: Final Answer: <answer>
"""

EXTRACT_ANSWER_PROMPT = """You are a strict answer extractor.
Extract the final answer from the text below.
The answer should be a number, a short phrase, or True/False.
Do not include "The answer is..." or any punctuation like periods at the end if it's a number.
If the answer is a number, output ONLY the number.

Text:
{text}

Final Answer:"""

PAL_ERROR_CORRECTION_PROMPT = """Your previous Python code failed to execute.
Please correct the code based on the error message.

Problem: {question}

Previous Code:
```python
{code}
```

Error Message:
{error}

Corrected Code:
```python
"""

SUMMARIZE_HISTORY_PROMPT = """The reasoning history is getting too long.
Summarize the following actions and observations concisely.
Keep the key numerical results and important errors.
Do not lose the context of what we are trying to solve.

History:
{history}

Summary:"""

COT_FACT_CHECK_PROMPT = """You are a strict reviewer. You have just generated a solution to a problem.
Now, double-check your own work for logic flaws or calculation errors.

Problem: {question}

Your Original Reasoning & Answer:
{reasoning}

Task:
1. Verify the calculations and logic.
2. If correct, repeat the final answer.
3. If incorrect, provide the corrected reasoning and answer.

Output format:
Final Answer: <answer>
"""
