import re
from .utils import call_model_chat_completions

class InferenceAgent:
    def __init__(self, model_name=None, verbose=False):
        self.model_name = model_name  
        self.verbose = verbose
        self.call_count = 0

    def solve(self, question: str) -> str:
        """
        Main entry point. Currently uses Chain-of-Thought.
        """
        self.call_count = 0
        return self.chain_of_thought(question)

    def chain_of_thought(self, question: str) -> str:
        
        # Construct the prompt
        system_prompt = (
            "You are an expert reasoning agent. "
            #"Thinking plan: MUST engage in thorough, systematic reasoning before EVERY response"
            "Go through the problem step by step"
            "Break down complex problems into components"
            #"Think through the problem step by step to ensure accuracy. "
            #"Provide the answer in a clear format."
            #"Reply with only the final answer—no explanation."
        )
        
        user_prompt = (
            f"Question: {question}\n\n"
            "Please solve this step-by-step.\n"
            "At the very end of your response, write the final answer strictly in this format: "
            "[[FINAL ANSWER: <your answer>]], True/False"
        )

        # Call the Model
        response = call_model_chat_completions(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.3 
        )

        self.call_count += 1

        if not response['ok']:
            return "Error: API call failed."

        full_text = response['text']

        if self.verbose:
            print(f"\n--- [DEBUG] Full Model Output ---")
            print(full_text)
            print(f"--- [DEBUG] End Output ---\n")

        # Extract the answer using Regex
        # We look for [[FINAL ANSWER: ... ]]
        match = re.search(r"\[\[FINAL ANSWER:\s*(.*?)\]\]", full_text, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        else:
            return full_text.strip()