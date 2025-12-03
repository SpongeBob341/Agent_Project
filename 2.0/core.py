import re
import collections
from typing import List, Optional, Tuple
from llm_client import LLMClient
import prompts
from tools import execute_python

class Agent:
    def __init__(self):
        self.llm = LLMClient()

    def solve(self, question: str) -> str:
        # 1. Analyze & Plan
        plan_output = self.plan(question)
        problem_type, plan_text, strategy = self.parse_plan(plan_output)
        
        print(f"\n[Plan] Type: {problem_type}, Strategy: {strategy}")
        
        # Execute Strategy with Self-Consistency 
        answers = []
        
        strategies_to_run = []
        if strategy == "Python":
            strategies_to_run = ["Python", "Python", "ReAct"]
        else:
            strategies_to_run = ["CoT", "CoT", "ReAct"]
            
        for i, s in enumerate(strategies_to_run):
            print(f"[Step {i+1}] Executing {s}...")
            ans = self.execute_strategy(question, plan_text, s)
            print(f"   -> Raw Result: {ans}")
            if ans:
                # Cleanup answer immediately
                cleaned = self.extract_final(ans)
                print(f"   -> Extracted: {cleaned}")
                if cleaned and cleaned != "Error":
                    answers.append(cleaned)
        
        # 3. Aggregate
        final_answer = self.aggregate_answers(answers)
        print(f"[Aggregate] Consensus: {final_answer}")
        
        # 4. Fallback / Self-Correction
        if not final_answer:
            print("[Self-Correction] Triggered...")
            # If we have NO answers or NO consensus, try self-correction
            final_answer = self.self_correct(question, answers)
            print(f"[Self-Correction] Result: {final_answer}")
            
        return str(final_answer)

    def plan(self, question: str) -> str:
        messages = [
            {"role": "system", "content": "You are a strategic planner."}, 
            {"role": "user", "content": prompts.PLANNER_PROMPT.format(question=question)}
        ]
        return self.llm.chat_completion(messages) or ""

    def parse_plan(self, plan_text: str) -> Tuple[str, str, str]:
        p_type = "Logic"
        strategy = "Reasoning"
        
        lower_plan = plan_text.lower()
        if "type: math" in lower_plan:
            p_type = "Math"
        elif "type: logic" in lower_plan:
            p_type = "Logic"
        elif "type: common sense" in lower_plan:
            p_type = "Common Sense"
            
        if "use python" in lower_plan:
            strategy = "Python"
        else:
            strategy = "Reasoning"
            
        return p_type, plan_text, strategy

    def execute_strategy(self, question: str, plan: str, strategy: str) -> Optional[str]:
        if strategy == "Python":
            return self.solve_pal(question, plan)
        elif strategy == "ReAct":
            return self.solve_react(question)
        else: # CoT
            return self.solve_cot(question, plan)

    def solve_pal(self, question: str, plan: str) -> Optional[str]:
        messages = [
            {"role": "user", "content": prompts.PAL_PROMPT.format(question=question, plan=plan)}
        ]
        response = self.llm.chat_completion(messages)
        
        if not response:
            return None
            
        # Try to execute up to 3 times (initial + 2 retries)
        current_code = None
        
        # Initial Extraction
        code_match = re.search(r"```python(.*?)```", response, re.DOTALL)
        if code_match:
            current_code = code_match.group(1)
        else:
            return None
        print(current_code)
        # Execution Loop
        for i in range(3):
            result = execute_python(current_code)
            
            # If success, return result
            if not result.startswith("Error:"):
                return result
                
            # If error, try to fix 
            if i < 2:
                print(f"   -> PAL Error: {result}")
                print("   -> Attempting to fix code...")
                
                fix_prompt = prompts.PAL_ERROR_CORRECTION_PROMPT.format(
                    question=question,
                    code=current_code,
                    error=result
                )
                
                # Ask LLM for fix
                messages.append({"role": "user", "content": fix_prompt})
                response = self.llm.chat_completion(messages)
                
                if not response:
                    break
                    
                code_match = re.search(r"```python(.*?)```", response, re.DOTALL)
                if code_match:
                    current_code = code_match.group(1)
                else:
                    break
                
        return None

    def solve_cot(self, question: str, plan: str) -> Optional[str]:
        messages = [
             {"role": "system", "content": "You are a logical reasoning expert."}, 
             {"role": "user", "content": prompts.COT_PROMPT.format(question=question, plan=plan)}
        ]
        response = self.llm.chat_completion(messages)
        return response

    def solve_react(self, question: str) -> Optional[str]:
        history = prompts.REACT_PROMPT.format(question=question)
        messages = [{"role": "user", "content": history}]
        
        for _ in range(7): # Max 7 steps
            response = self.llm.chat_completion(messages, stop=["Observation:"])
            if not response:
                break
                
            messages.append({"role": "assistant", "content": response})
            
            if "Final Answer:" in response:
                return response.split("Final Answer:")[-1].strip()
            
            if "Action: Python Code" in response:
                code_match = re.search(r"```python(.*?)```", response, re.DOTALL)
                if code_match:
                    code = code_match.group(1)
                    obs = execute_python(code)
                    messages.append({"role": "user", "content": f"Observation: {obs}\n"})
                else:
                    messages.append({"role": "user", "content": "Observation: Error: No code block found.\n"})
            elif "Action: None" in response:
                 messages.append({"role": "user", "content": "Observation: Continue reasoning.\n"})
            else:
                 # If model forgets format, nudge it
                 messages.append({"role": "user", "content": "Observation: Invalid format. Please use Action: [Python Code / None]\n"})
        
        return None

    def aggregate_answers(self, answers: List[str]) -> Optional[str]:
        if not answers:
            return None
        
        # Normalize
        norm_answers = [self.normalize(a) for a in answers]
        
        # Filter empty
        norm_answers = [a for a in norm_answers if a]
        
        if not norm_answers:
            return None

        counts = collections.Counter(norm_answers)
        most_common_pair = counts.most_common(1)
        if not most_common_pair:
            return None
            
        most_common, count = most_common_pair[0]
        
        # Relaxed majority
        if count >= 2:
            return most_common
        
        return None

    def self_correct(self, question: str, previous_answers: List[str]) -> str:
        attempts_str = "\n".join([f"- {a}" for a in previous_answers])
        prompt = prompts.SELF_CORRECTION_PROMPT.format(question=question, attempts=attempts_str)
        
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.chat_completion(messages)
        return self.extract_final(response)

    def normalize(self, text: str) -> str:
        if not text: return ""
        text = str(text).strip().lower()
        try:
            val = float(text)
            if val.is_integer():
                return str(int(val))
            return str(val)
        except:
            pass
        return text

    def extract_final(self, text: Optional[str]) -> str:
        if not text: 
            return "Error_extract1"
        # Heuristic: if text is just a number, return it
        if text.strip().replace(".","").isdigit():
             return text.strip()
        print(text)
        messages = [
            {"role": "user", "content": prompts.EXTRACT_ANSWER_PROMPT.format(text=text)}
        ]
        res = self.llm.chat_completion(messages)
        #print(res)
        return res.strip() if res else "Error_extract2"
