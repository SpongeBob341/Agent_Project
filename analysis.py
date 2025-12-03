import re

def analyze_test_results(file_path):
    # Dictionary to store stats: {'domain_name': {'total': 0, 'correct': 0}}
    domain_stats = {}
    
    overall_total = 0
    overall_correct = 0
    
    current_domain = None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # 1. Look for the Domain line: e.g., [Question 1] (math)
                # Regex explanation: Look for square brackets, then capture text inside ()
                domain_match = re.search(r'\[Question \d+\] \((.*?)\)', line)
                
                if domain_match:
                    # Found a new question, set the current domain
                    current_domain = domain_match.group(1).strip()
                    
                    # Initialize this domain in our dictionary if it's new
                    if current_domain not in domain_stats:
                        domain_stats[current_domain] = {'total': 0, 'correct': 0}
                
                # 2. Look for the Result line: e.g., Result: CORRECT
                result_match = re.search(r'Result: (CORRECT|INCORRECT)', line)
                
                if result_match and current_domain:
                    result = result_match.group(1)
                    
                    # Update Domain specific stats
                    domain_stats[current_domain]['total'] += 1
                    if result == 'CORRECT':
                        domain_stats[current_domain]['correct'] += 1
                    
                    # Update Overall stats
                    overall_total += 1
                    if result == 'CORRECT':
                        overall_correct += 1

        # --- PRINTING THE REPORT ---
        print("-" * 40)
        print(f"{'DOMAIN REPORT':^40}")
        print("-" * 40)
        
        # specific domain breakdown
        for domain, stats in domain_stats.items():
            d_total = stats['total']
            d_correct = stats['correct']
            d_incorrect = d_total - d_correct
            # Avoid division by zero
            d_acc = (d_correct / d_total * 100) if d_total > 0 else 0
            
            print(f"Domain: {domain.upper()}")
            print(f"  • Total Questions: {d_total}")
            print(f"  • Correct:   {d_correct}")
            print(f"  • Incorrect: {d_incorrect}")
            print(f"  • Accuracy:  {d_acc:.2f}%")
            print("-" * 20)

        # Final Summary
        print("\n" + "=" * 40)
        print(f"{'FINAL SUMMARY':^40}")
        print("=" * 40)
        
        print(f"Total Domains Found: {len(domain_stats)}")
        print(f"Total Questions:     {overall_total}")
        print(f"Total Correct:       {overall_correct}")
        print(f"Total Incorrect:     {overall_total - overall_correct}")
        
        final_accuracy = (overall_correct / overall_total * 100) if overall_total > 0 else 0
        print(f"OVERALL ACCURACY:    {final_accuracy:.2f}%")
        print("=" * 40)

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

# --- CONFIGURATION ---
# Change this to match your actual text file name
file_name = 'log.txt' 

# Run the function
if __name__ == "__main__":
    analyze_test_results(file_name)