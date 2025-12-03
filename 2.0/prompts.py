
PLANNER_PROMPT = """You are an intelligent problem solver.
Your goal is to analyze the given user question and create a step-by-step plan to solve it.

1. Identify the type of problem: "Math", "Logic", or "Common Sense".
2. Break down the problem into logical steps.
3. Determine if Python code would be useful (e.g., for calculations, simulations) or if verbal reasoning is better.

Question: {question}

Output format:
Type: [Math/Logic/Common Sense]
Plan:
1. ...
2. ...
Recommendation: [Use Python/Use Reasoning]
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

COT_PROMPT = """You are a logical reasoning expert, you work with facts and nothing else. Solve the following problem step-by-step.

Problem: {question}
Plan: {plan}

Think step by step.
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
... (this Thought/Action/Observation can repeat N times)
Thought: I have the final answer
Final Answer: [The final answer]

Question: {question}
"""

SELF_CORRECTION_PROMPT = """The previous attempts to solve the problem failed or produced inconsistent results.
Problem: {question}

Previous Attempts/Errors:
{attempts}

Analyze why these might have failed.
Then, provide a NEW, BETTER prompt or strategy to solve it.
Finally, try to solve it yourself using that new perspective.
Only output the Final Answer in the end.
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
