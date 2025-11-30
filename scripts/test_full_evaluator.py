from core.parsing.evaluators.full_evaluator import FullResumeEvaluator
import json
import os

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def main():
    evaluator = FullResumeEvaluator()
    
    data_dir = "/home/acer/Desktop/cv/core/parsing/tests_data/resume_and_texts_kaggle/some"
    files = [f for f in os.listdir(data_dir) if f.endswith(".json")]
    
    if len(files) < 2:
        print("Not enough JSON files for comparison.")
        return
        
    # Load two different files to simulate GT vs Predicted
    gt_path = os.path.join(data_dir, files[0])
    pred_path = os.path.join(data_dir, files[1])
    
    print(f"Comparing {files[0]} (GT) vs {files[1]} (Pred)...")
    print("=" * 60)
    
    gt_data = load_json(gt_path)
    pred_data = load_json(pred_path)
    
    # Run full resume evaluation
    results = evaluator.evaluate_resume(gt_data, pred_data)
    
    # Display results for each section
    for section, metrics in results.items():
        print(f"\n{section.upper()}:")
        print(f"  Precision: {metrics['precision']:.2f}")
        print(f"  Recall:    {metrics['recall']:.2f}")
        print(f"  F1:        {metrics['f1']:.2f}")
        
        if metrics.get('field_scores'):
            print(f"  Field Scores:")
            for field, score in metrics['field_scores'].items():
                print(f"    - {field}: {score:.2f}")
    
    print("\n" + "=" * 60)
    print("Full resume evaluation complete!")

if __name__ == "__main__":
    main()
