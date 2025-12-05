import json
import re
from core import Agent

# Normalization helpers from the tutorial
def normalize_text(s: str) -> str:
    s = (s or "").strip().lower()
    # Remove surrounding punctuation and extra whitespace
    s = re.sub(r"[^\w\s\-']", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def extract_number(s: str):
    # Returns first number occurrence as string if found, else None
    if not s:
        return None
    # Match number: optional sign, digits, optional decimal
    m = re.search(r"[-+]?\d+(\.\d+)?", s)
    return m.group(0) if m else None

def grade_answer(expected: str, got: str) -> bool:
    # Try numeric match first
    exp_num = extract_number(expected)
    got_num = extract_number(got)
    if exp_num is not None and got_num is not None:
        try:
            return float(exp_num) == float(got_num)
        except:
            pass
            
    # Fallback to text normalization
    return normalize_text(got) == normalize_text(expected)

def analyze_file(log_file_path: str):
    """
    Parses a log file with lines:
    Expected: <val>
    Agent Output: <val>
    """
    total = 0
    correct = 0
    
    with open(log_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # We split by the separator used in test_dev.py (dashed line)
    blocks = content.split("-" * 20)
    
    for block in blocks:
        if not block.strip(): continue
        
        exp_match = re.search(r"Expected:\s*(.*)", block)
        got_match = re.search(r"Agent Output:\s*(.*)", block)
        
        if exp_match and got_match:
            expected = exp_match.group(1).strip()
            got = got_match.group(1).strip()
            
            is_correct = grade_answer(expected, got)
            total += 1
            if is_correct:
                correct += 1
            

    print(f"Total: {total}")
    print(f"Correct: {correct}")
    if total > 0:
        print(f"Accuracy: {correct/total*100:.2f}%")

def run_and_evaluate_dev(limit: int = 5):
    print(f"Running evaluation on first {limit} dev examples...")
    
    with open("cse476_final_project_dev_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    subset = data[:limit]
    agent = Agent()
    
    total = 0
    correct = 0
    
    results = []
    
    for i, item in enumerate(subset):
        print(f"--- Question {i+1} ---")
        print(f"Input: {item['input']}")
        
        # Run Agent
        prediction = agent.solve(item['input'])
        expected = item.get('output', '')
        
        print(f"Expected: {expected}")
        print(f"Agent Output: {prediction}")
        
        is_correct = grade_answer(expected, prediction)
        if is_correct:
            print("Result: CORRECT")
            correct += 1
        else:
            print("Result: INCORRECT")
        
        total += 1
        print("-" * 20)
        
        results.append({
            "input": item['input'],
            "expected": expected,
            "got": prediction,
            "correct": is_correct
        })

    print("\n=== Final Report ===")
    print(f"Total: {total}")
    print(f"Correct: {correct}")
    if total > 0:
        print(f"Accuracy: {correct/total*100:.2f}%")
        
if __name__ == "__main__":
    # If arguments provided, could parse file, otherwise run dev
    import sys
    if len(sys.argv) > 1 and sys.argv[1].endswith(".txt"):
        analyze_file(sys.argv[1])
    else:
        # Run on a subset (e.g. 5) to test quickly
        run_and_evaluate_dev(limit=250)
