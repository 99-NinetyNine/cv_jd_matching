from core.evaluation.evaluator import Evaluator
import json

def main():
    evaluator = Evaluator()
    
    # Mock Ground Truth
    ground_truth = [
        {"name": "Google", "position": "Software Engineer", "startDate": "2020-01", "summary": "Worked on Search."},
        {"name": "Facebook", "position": "Intern", "startDate": "2019-06", "summary": "React development."}
    ]
    
    # Mock Predicted (Order swapped, slight typo, partial match)
    predicted = [
        {"name": "Facebook Inc", "position": "Internship", "startDate": "2019-06", "summary": "React dev."},
        {"name": "Google", "position": "Senior SWE", "startDate": "2020-01", "summary": "Search engine work."}
    ]
    
    config = {
        "key_fields": ["name", "position"],
        "fields": {
            "name": "substring",
            "position": "substring",
            "startDate": "exact",
            "summary": "text_similarity"
        }
    }
    
    print("Evaluating Work Section...")
    metrics = evaluator.evaluate_section(ground_truth, predicted, config)
    
    print(json.dumps(metrics, indent=2))
    
    # Check if alignment worked (Google should match Google, FB should match FB)
    # Precision/Recall should be 1.0 because we have 2 items and both match well enough
    if metrics["precision"] == 1.0 and metrics["recall"] == 1.0:
        print("SUCCESS: Alignment and matching working as expected.")
    else:
        print("FAILED: Metrics lower than expected.")

if __name__ == "__main__":
    main()
