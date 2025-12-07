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
        # Analyze & Plan
        plan_output = self.plan(question)
        problem_type, plan_text, strategy = self.parse_plan(plan_output)
        
        #print(f"\n[Plan] Type: {problem_type}, Strategy: {strategy}")
        
        # Execute Strategy with Self-Consistency 
        answers = []
        
        strategies_to_run = []
        if strategy == "Python":
            strategies_to_run = ["Python", "Python", "CoT"]
        else:
            strategies_to_run = ["CoT", "CoT", "ReAct"]
            
        for i, s in enumerate(strategies_to_run):
            #print(f"[Step {i+1}] Executing {s}...")
            ans = self.execute_strategy(question, plan_text, s, problem_type)
            #print(f"   -> Raw Result: {ans}")
            if ans:
                # Cleanup answer immediately
                cleaned = self.extract_final(ans)
                #print(f"   -> Extracted: {cleaned}")
                if cleaned and cleaned != "Error":
                    answers.append(cleaned)
        
        # Aggregate (Self Consistency)
        final_answer = self.aggregate_answers(answers)
        #print(f"[Aggregate] Consensus: {final_answer}")
        
        # Fallback / Self Correction (If we have NO answers or NO consensus, try self correction)
        if not final_answer:
            #print("[Self-Correction] Triggered...")
            final_answer = self.self_correct(question, answers)
            #print(f"[Self-Correction] Result: {final_answer}")
            
        return str(final_answer)

    # Make a Strategic plan for the question
    def plan(self, question: str) -> str:
        messages = [
            {"role": "system", "content": "You are a strategic planner."}, 
            {"role": "user", "content": prompts.PLANNER_PROMPT.format(question=question)}
        ]
        return self.llm.chat_completion(messages) or ""

    # Parse the plan to extract information
    def parse_plan(self, plan_text: str) -> Tuple[str, str, str]:
        p_type = "Logic"
        strategy = "Reasoning"
        plan_content = plan_text
        
        type_match = re.search(r"PROBLEM_TYPE:\s*(Math|Logic|Common Sense)", plan_text, re.IGNORECASE)
        if type_match:
            p_type = type_match.group(1).strip()
            
        strategy_match = re.search(r"STRATEGY_RECOMMENDATION:\s*(Use Python|Use Reasoning)", plan_text, re.IGNORECASE)
        if strategy_match:
            strategy = strategy_match.group(1).replace("Use ", "").strip() # "Python" or "Reasoning"
            
        # Extract the actual plan text (everything between PLAN: and STRATEGY_RECOMMENDATION:)
        plan_content_match = re.search(r"PLAN:(.*?)STRATEGY_RECOMMENDATION:", plan_text, re.DOTALL)
        if plan_content_match:
            plan_content = plan_content_match.group(1).strip()

        return p_type, plan_content, strategy

    # Exceute diffrent strategies
    def execute_strategy(self, question: str, plan: str, strategy: str, problem_type: str = "Logic") -> Optional[str]:
        if strategy == "Python":
            return self.solve_pal(question, plan)
        elif strategy == "ReAct":
            return self.solve_react(question)
        else: # CoT
            return self.solve_cot(question, plan, problem_type)

    # Python solver
    def solve_pal(self, question: str, plan: str) -> Optional[str]:
        messages = [
            {"role": "user", "content": prompts.PAL_PROMPT.format(question=question, plan=plan)}
        ]
        response = self.llm.chat_completion(messages)
        
        if not response:
            return None
            
        
        current_code = None
        
        # Initial Extraction
        code_match = re.search(r"```python(.*?)```", response, re.DOTALL)
        if code_match:
            current_code = code_match.group(1)
        else:
            return None
        
        
        # Execution Loop   3 runs (initial + 2 retries)
        for i in range(3):
            result = execute_python(current_code)
            
            # If success, return result
            if not result.startswith("Error:"):
                return result
                
            # If error, try to fix 
            if i < 2:
                #print(f"   -> PAL Error: {result}")
                #print("   -> Attempting to fix code...")
                
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

    def solve_cot(self, question: str, plan: str, problem_type: str = "Logic") -> Optional[str]:
        messages = [
             {"role": "user", "content": prompts.COT_PROMPT.format(question=question, plan=plan)}
        ]
        response = self.llm.chat_completion(messages)

        # Fact Check for Common Sense / Logic types
        if response and problem_type in ["Common Sense", "Logic"]:
            #print("   [CoT] Fact checking response...")
            check_msg = [
                {"role": "user", "content": prompts.COT_FACT_CHECK_PROMPT.format(question=question, reasoning=response)}
            ]
            checked_response = self.llm.chat_completion(check_msg)
            if checked_response:
                return checked_response
                
        return response

    def solve_react(self, question: str) -> Optional[str]:
        history = prompts.REACT_PROMPT.format(question=question)
        messages = [{"role": "user", "content": history}]
        
        for i in range(7): # Max 7 steps
            total_chars = sum(len(m["content"]) for m in messages)
            #print(f"   [ReAct Step {i+1}] History Length: {total_chars} chars")
            
            # Context management: Summarize if too long
            if total_chars > 10000: 
                self.summarize_history(messages)
                
            response = self.llm.chat_completion(messages, stop=["Observation:"])
            if not response:
                break
            
            # Message is a cumilation of all react response
            messages.append({"role": "assistant", "content": response})
            
            if "Final Answer:" in response:
                return response.split("Final Answer:")[-1].strip()
            
            if "Action: Python Code" in response:
                code_match = re.search(r"```python(.*?)```", response, re.DOTALL)
                if code_match:
                    code = code_match.group(1)
                    # If code is excessively long, don't execute it, just return an error
                    if len(code) > 3000: 
                        obs = "Error: Generated code was too long. Please write concise code."
                    else:
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

    def summarize_history(self, messages: List[dict]):
        # Keep the first message (Prompt + Question)
        # Summarize everything else except the very last one (to keep continuity)
                
        to_summarize = messages[1:-1]
        history_text = "\n".join([f"{m['role']}: {m['content']}" for m in to_summarize])
        
        prompt = prompts.SUMMARIZE_HISTORY_PROMPT.format(history=history_text)
        summary = self.llm.chat_completion([{"role": "user", "content": prompt}])
        
        if summary:
            # Replace the middle with the summary
            messages[1:-1] = [{"role": "system", "content": f"Previous Steps Summary:\n{summary}"}]

    # Self Consistency, look for most common output
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

    # Generate a prompt for itself and then solve if nothing works
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
        if not text: return "Error"
        text = str(text).strip()
        #print(text)
        
        # Look for \boxed{...} (common in math)
        boxed_match = re.search(r"\\boxed\{(.*?)\}", text)
        if boxed_match:
            return boxed_match.group(1)
        
        # Look for python code block
        ans_match = re.search(r"```python\n(.*?)```", text, re.DOTALL)
        if ans_match:
            return ans_match.group(1).strip() 
            
        # Look for "Final Answer: ..."
        fa_match = re.search(r"Final Answer\s*(.*)", text, re.IGNORECASE | re.DOTALL)
        if fa_match:
            # Take everything after final answer
            raw_output = fa_match.group(1).strip().split('\n')[0]
            return raw_output
        
    
        # Fallback: If it looks like a single number or short phrase (e.g. from PAL output), return it
        lines = [L.strip() for L in text.split('\n') if L.strip()]
        if lines:
            last_line = lines[-1]
            # If it's short enough, assume it's the answer
            if len(last_line) < 100:
                return last_line
                
        return text
