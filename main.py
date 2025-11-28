import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.utils import call_model_chat_completions

def main():
    print("--- Starting Agent Smoke Test ---")
    
    demo_prompt = "What is 17 + 28? Answer with just the number."
    print(f"Prompt: {demo_prompt}")

    result = call_model_chat_completions(
        demo_prompt, 
        system="You are a helpful assistant. Reply with only the final answer."
    )

    if result["ok"]:
        print("\nSUCCESS: API call worked.")
        print(f"Status Code: {result['status']}")
        print(f"Model Output: {result['text'].strip()}")
    else:
        print("\nFAILURE: API call failed.")
        print(f"Status Code: {result['status']}")
        print(f"Error Message: {result['error']}")

if __name__ == "__main__":
    main()