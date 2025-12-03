import re
import json
import sys
import io
import contextlib
from collections import Counter
from .utils import call_model_chat_completions

class InferenceAgent:
    def __init__(self, model_name=None, verbose=False):
        self.model_name = model_name  
        self.verbose = verbose
        self.call_count = 0

    def solve(self, question: str) -> str:
        """
        Main entry point with Router logic and Reflexion (Self-Correction).
        """
        self.call_count = 0
        
        # Router Step
        router_prompt = (
            f"Classify the following question into exactly one of these categories: "
            f"[MATH, LOGIC, COMMON_SENSE]\n\n"
            f"Question: {question}\n\n"
            f"Reply with ONLY the category name."
        )
        
        classification_resp = call_model_chat_completions(
            prompt=router_prompt,
            system="You are a classifier. Reply only with the category name.",
            temperature=0.1
        )
        self.call_count += 1
        
        category = (classification_resp['text'] or "").strip().upper()
        
        if self.verbose:
            print(f"\n[Router] Classified as: {category}")

        # Generate Initial Candidate Answer
        initial_answer = ""
        if "MATH" in category:
            # Switch to ReAct for math to allow iterative solving and tool use
            initial_answer = self.react_chain(question)
        elif "LOGIC" in category:
             initial_answer = self.react_chain(question)
        else:
            initial_answer = self.self_consistency(question, num_samples=5)

        # Reflexion Step (Verify and Refine)
        final_answer = self.verify_and_refine(question, initial_answer)
        
        return final_answer

    def verify_and_refine(self, question: str, initial_answer: str) -> str:
        """
        Reflexion Loop:
        Critiques the initial answer and attempts to correct it if flawed.
        """
        if self.verbose:
            print(f"\n--- Starting Reflexion on Answer: {initial_answer} ---")

        # Check for obvious error messages first to save a call
        if "Error" in initial_answer and "execution failed" in initial_answer:
             pass

        prompt = (
            f"Question: {question}\n"
            f"Proposed Answer: {initial_answer}\n\n"
            f"Review the Proposed Answer for correctness. "
            f"Check for logical fallacies, calculation errors, or factual inaccuracies.\n"
            f"If the answer is correct, reply with exactly: [[VALID]]\n"
            f"If the answer is incorrect, explain why and provide the correct Final Answer.\n"
            f"End your response with the corrected answer in the format: [[FINAL ANSWER: <answer>]]"
        )

        response = call_model_chat_completions(
            prompt=prompt,
            system="You are a strict reviewer. Verify the answer carefully.",
            temperature=0.0
        )
        self.call_count += 1
        
        if not response['ok']:
            return initial_answer # Fallback

        critique = response['text'].strip()
        
        if self.verbose:
            print(f"[Reflexion Critique]\n{critique}")

        if "[[VALID]]" in critique:
            if self.verbose:
                print("Answer validated.")
            return initial_answer
        
        # Extract corrected answer
        match = re.search(r"((\[\[FINAL ANSWER:.*?\]\]))", critique, re.DOTALL)
        if match:
            corrected_answer = match.group(1).strip()
            if self.verbose:
                print(f"Answer refined to: {corrected_answer}")
            return corrected_answer
            
        return initial_answer

    def execute_python(self, code: str) -> str:
        """
        Executes the provided Python code and returns stdout.
        Captures errors if they occur.
        """
        output_buffer = io.StringIO()
        try:
            # Redirect stdout to capture print statements
            with contextlib.redirect_stdout(output_buffer):
                # Define a safe-ish local scope
                local_scope = {}
                exec(code, {'__name__': '__main__', 'print': print}, local_scope)
            return output_buffer.getvalue().strip()
        except Exception as e:
            return f"Error executing code: {e}"

    def pal_chain(self, question: str) -> str:
        """
        Algorithm 3: Program-Aided Language Models (PAL) with Plan-and-Solve.
        1. Generates a step-by-step plan (CoT).
        2. Generates Python code based on the plan.
        3. Executes code with retries.
        """
        if self.verbose:
            print(f"\n--- Starting PAL (Plan-and-Solve) for: {question} ---")

        # Generate the Plan (CoT)
        plan_prompt = (
            f"Question: {question}\n\n"
            "Please analyze this problem and create a step-by-step algorithm to solve it. "
            "Do not write Python code yet. Just describe the logical steps and formulas needed."
        )
        
        plan_resp = call_model_chat_completions(
            prompt=plan_prompt,
            system="You are a math expert. Create a clear solution plan.",
            temperature=0.4
        )
        self.call_count += 1
        
        plan = (plan_resp['text'] or "").strip()
        if self.verbose:
            print(f"\n[PAL Plan]\n{plan}\n")

        # Generate Code based on the Plan
        system_prompt = (
            "You are a Python expert. Write a Python script to solve the given problem based on the provided plan. "
            "IMPORTANT: You must PRINT the final answer at the very end of the script. "
            "Do not just calculate it; use `print(...)` to output it. "
            "Wrap your code in markdown code blocks ```python ... ```."
        )
        
        history = f"Question: {question}\n\nPlan:\n{plan}\n\nWrite the Python code now."
        
        max_retries = 5
        for attempt in range(max_retries + 1):
            response = call_model_chat_completions(
                prompt=history,
                system=system_prompt,
                temperature=0.2
            )
            self.call_count += 1

            if not response['ok']:
                return "Error: API call failed during PAL."

            text = response['text']
            
            # Extract code block
            code_match = re.search(r"```python(.*?)```", text, re.DOTALL)
            if not code_match:
                code_match = re.search(r"```(.*?)```", text, re.DOTALL)
                
            if code_match:
                code = code_match.group(1).strip()
                if self.verbose:
                    print(f"\n[PAL] Generated Code (Attempt {attempt+1}):\n{code}\n")
                
                # Execute code
                result = self.execute_python(code)
                
                if self.verbose:
                    print(f"[PAL] Execution Result: {result}")
                
                # Check for execution errors
                if "Error executing code" in result:
                    if attempt < max_retries:
                        if self.verbose:
                            print(f"[PAL] Code execution failed. Retrying...")
                        history += f"\n\nYour previous code failed with this error:\n{result}\n\nPlease fix the code and output the corrected Python script."
                        continue
                    else:
                        return f"Error: Code execution failed after {max_retries+1} attempts. Last error: {result}"

                if not result:
                    if attempt < max_retries:
                        if self.verbose:
                            print(f"[PAL] No output captured. Retrying...")
                        history += f"\n\nYour code executed but printed nothing. Please ensure you use `print(answer)` at the end."
                        continue
                    else:
                        return "Error: No output from Python script."
                
                return result
            else:
                if attempt < max_retries:
                    if self.verbose:
                        print(f"[PAL] No code block found. Retrying...")
                    history += f"\n\nI could not find a code block in your response. Please wrap your code in ```python ... ```."
                    continue
                else:
                    return "Error: No code block found in response."
        
        return "Error: Max retries reached in PAL."

    def react_chain(self, question: str, max_turns: int = 5) -> str:
        """
        Algorithm 4: ReAct (Reasoning + Acting)
        Interleaves reasoning (Thought), actions (Action/Action Input), and results (Observation).
        Supported Tools: [Python]
        """
        if self.verbose:
            print(f"\n--- Starting ReAct for: {question} ---")

        system_prompt = (
            "You are a smart reasoning agent. Solve the question using a ReAct loop.\n"
            "You have access to the following tool:\n"
            " - Python: Useful for performing calculations or complex logic. Input should be valid python code.\n"
            "   IMPORTANT: You MUST `print(...)` the result of your calculation to see the output in the Observation.\n"
            "   Example: `print(15 * 4)`\n\n"
            "Use the following format:\n"
            "Question: the input question\n"
            "Thought: you should always think about what to do\n"
            "Action: the action to take\n"
            "Action Input: the input to the action \n"
            "Observation: the result of the action\n"
            "... (this Thought/Action/Action Input/Observation can repeat N times)\n"
            "Thought: I now know the final answer\n"
            "Final Answer: the final answer to the original input question in one word(True/False) or value\n\n"
            "Begin!"
        )

        # Initialize conversation with the question
        history = f"Question: {question}\n"

        for i in range(max_turns):
            response = call_model_chat_completions(
                prompt=history,
                system=system_prompt,
                temperature=0.5,
            )
            self.call_count += 1
            
            if not response['ok']:
                print(f"\nAPI REQUEST FAILED")
                print(json.dumps(response, indent=2, default=str)) 
                return "Error: API call failed."
                
            step_text = response['text'].strip()
            
            if "Observation:" in step_text:
                step_text = step_text.split("Observation:")[0].strip()

            history += step_text + "\n"
            
            if self.verbose:
                print(f"\n[ReAct Step {i+1}]\n{step_text}")

            # Check for Final Answer
            if "Final Answer:" in step_text:
                return step_text.split("Final Answer:")[1].strip()

            # Parse Action
            
            action_match = re.search(r"Action:\s*(.*)", step_text, re.IGNORECASE)
            input_match = re.search(r"Action Input:\s*(.*)", step_text, re.DOTALL | re.IGNORECASE)

            if action_match and input_match:
                action = action_match.group(1).strip()
                action_input = input_match.group(1).strip()
                
                action_input = action_input.replace("```python", "").replace("```", "").strip()

                observation = ""
                if action.lower() == "python":
                    if self.verbose:
                        print(f"[ReAct Action] Running Python code...")
                    observation = self.execute_python(action_input)
                else:
                    observation = f"Error: Unknown tool '{action}'"

                obs_str = f"Observation: {observation}\n"
                history += obs_str
                
                if self.verbose:
                    print(f"[ReAct Observation] {observation}")
            else:
                if self.verbose:
                    print("[ReAct] No action detected. Asking to continue...")
                history += "Observation: Invalid format. Please follow Thought -> Action -> Action Input format or provide Final Answer.\n"

        return "Error: Max ReAct turns reached without Final Answer."

    def chain_of_thought(self, question: str) -> str:
        
        # Construct the prompt
        system_prompt = (
            "You are a reasoning agent. "
            "Go through the problem step by step"
            
            
            #"Break down complex problems into components"
            #"Think through the problem step by step to ensure accuracy. "
            #"Provide the answer in a clear format."
            #"Reply with only the final answer—no explanation."
        )
        
        user_prompt = (
            f"Question: {question}\n\n"
            #"Please solve this step-by-step.\n"
            "At the very end of your response, write the final answer strictly in this format: "
            "[[FINAL ANSWER: <your answer>]], True/False"
        )

        # Call the Model
        response = call_model_chat_completions(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.6
        )

        self.call_count += 1

        # if not response['ok']:
        #     return "Error: API call failed."

        if not response['ok']:
            print(f"\nAPI REQUEST FAILED")
            print(json.dumps(response, indent=2, default=str)) 
            return "Error: API call failed."

        full_text = response['text']

        if self.verbose:
            print(f"\n--- [DEBUG] Full Model Output ---")
            print(full_text)
            print(f"--- [DEBUG] End Output ---\n")

        # Extract the answer using Regex
        # [[FINAL ANSWER: ... ]]
        match = re.search(r"((\[\[FINAL ANSWER:.*?\]\]))", full_text, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        else:
            return full_text.strip()
        
    def self_consistency(self, question: str, num_samples: int = 5) -> str:
        """
        Algorithm 2: Self-Consistency (Majority Voting)
        """
        answers = []
        
        if self.verbose:
            print(f"--- Starting Self-Consistency (k={num_samples}) ---")

        for i in range(num_samples):
            # We reuse the chain_of_thought method to get a single answer
            ans = self.chain_of_thought(question)
            answers.append(ans)

        counts = Counter(answers)
        most_common, frequency = counts.most_common(1)[0]
        
        if self.verbose:
            print(f"--- Votes: {dict(counts)} ---")
            print(f"--- Winner: {most_common} (with {frequency}/{num_samples} votes) ---")
            
        return most_common