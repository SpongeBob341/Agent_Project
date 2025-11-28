import re
from .utils import call_model_chat_completions

class InferenceAgent:
    def __init__(self, model_name=None, verbose=False):
        self.model_name = model_name  
        self.verbose = verbose

    def solve(self, question: str) -> str:
        """
        Main entry point. Currently uses Chain-of-Thought.
        Future updates will add logic to select between methods (CoT, Self-Consistency, etc.)
        """
        return self.chain_of_thought(question)

    def chain_of_thought(self, question: str) -> str:
        """
        Algorithm 1: Chain-of-Thought.
        Asks the model to think step-by-step, then extracts the answer.
        """
        # Construct the prompt
        system_prompt = (
            "You are an expert reasoning agent. "
            "Think through the problem first to ensure accuracy. "
            "Finally, provide the answer in a clear format."
        )
        
        user_prompt = (
            f"Question: {question}\n\n"
            "Please solve this step-by-step.\n"
            "At the very end of your response, write the final answer strictly in this format: "
            "[[FINAL ANSWER: <your answer>]]"
        )

        # Call the Model
        response = call_model_chat_completions(
            prompt=user_prompt,
            system=system_prompt,
            temperature=0.3 
        )

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