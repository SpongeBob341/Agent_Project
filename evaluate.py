import json
import sys
import os
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

#from src.inference_agent import InferenceAgent
from src.inference_agent_legacy import InferenceAgent

DEV_DATA_PATH = Path("data/cse476_final_project_dev_data.json")

def normalize_answer(text):
    """
    Simple normalization to match the dev data format.
    Removes whitespace and converts to lower case.
    Also handles float-to-int conversion for numeric answers.
    """
    if text is None:
        return ""
    s = str(text).strip().lower()
    
    # Try to convert to number and back to string to handle 20.0 == 20
    try:
        f_val = float(s)
        if f_val.is_integer():
            return str(int(f_val))
        else:
            # For non-integers, maybe limit precision or just return as is
            return str(f_val)
    except ValueError:
        pass
        
    return s

def main():
    if not DEV_DATA_PATH.exists():
        print(f"Error: File not found at {DEV_DATA_PATH}")
        return

    print(f"Loading data from {DEV_DATA_PATH}...")
    with open(DEV_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    agent = InferenceAgent(verbose=True)
    
    correct_count = 0
    total_count = 0
    
    # limit number of questions for a quick test
    subset_data = data[0:5] #+ data[700:710]

    print(f"--- Starting Evaluation on {len(subset_data)} items ---")

    for i, item in enumerate(subset_data):
        question = item["input"]
        expected = item["output"]
        domain = item.get("domain", "unknown")

        print(f"\n[Question {i+1}] ({domain})")
        print(f"Input: {question[:100]}...") 
        
        # Run Agent
        prediction = agent.solve(question)
        
        # Check Answer
        is_correct = normalize_answer(prediction) == normalize_answer(expected)
        
        print(f"Expected: {expected}")
        print(f"Predicted: {prediction}")
        print(f'LLMs calls: {agent.call_count}')
        print(f"Result: {'CORRECT' if is_correct else 'INCORRECT'}")

        if is_correct:
            correct_count += 1
        total_count += 1

    accuracy = (correct_count / total_count) * 100
    print(f"\n--- Final Results ---")
    print(f"Accuracy: {accuracy:.2f}% ({correct_count}/{total_count})")

if __name__ == "__main__":
    main()