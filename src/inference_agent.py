import re
import json
from collections import Counter
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
        #return self.chain_of_thought(question)
        return self.self_consistency(question,10)

    def chain_of_thought(self, question: str) -> str:
        
        # Construct the prompt
        system_prompt = (
            "You are a reasoning agent. "
            "Go through the problem step by step"
            "Thinking plan: if its a maths related question use python"
            
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
        match = re.search(r"\[\[FINAL ANSWER:\s*(.*?)\]\]", full_text, re.DOTALL)
        
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