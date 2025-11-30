from core.parsing.evaluators.evaluator import HungarianEvaluator
import json
import os

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def main():
    evaluator = HungarianEvaluator()
    
    data_dir = "/home/acer/Desktop/cv/core/parsing/tests_data/resume_and_texts_kaggle/some"
    files = [f for f in os.listdir(data_dir) if f.endswith(".json")]
    
    if len(files) < 2:
        print("Not enough JSON files for comparison.")
        return
        
    # Load two different files to simulate GT vs Predicted (just for testing metrics)
    gt_path = os.path.join(data_dir, files[0])
    pred_path = os.path.join(data_dir, files[1])
    
    print(f"Comparing {files[0]} (GT) vs {files[1]} (Pred)...")
    
    gt_data = load_json(gt_path)
    pred_data = load_json(pred_path)
    
    # Compare 'work' section
    gt_work = gt_data.get("work", [])
    pred_work = pred_data.get("work", [])
    
    config = {
        "key_fields": ["name", "position"],
        "fields": {
            "name": "substring",
            "position": "substring",
            "startDate": "date",
            "summary": "text_similarity"
        }
    }
    
    print("Evaluating Work Section...")
    metrics = evaluator.evaluate_section(gt_work, pred_work, config)
    
    print(json.dumps(metrics, indent=2))
    
    if metrics["precision"] < 1.0 or metrics["recall"] < 1.0:
        print("SUCCESS: Metrics reflect differences as expected.")
    else:
        print("WARNING: Metrics are perfect, which is unexpected for different files.")

if __name__ == "__main__":
    main()
