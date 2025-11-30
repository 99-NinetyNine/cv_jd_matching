from core.pipeline import ResumeExtractionPipeline
import os
import json

def main():
    pipeline = ResumeExtractionPipeline()
    input_dir = "data/synthetic_verification"
    output_dir = "data/pipeline_output"
    
    print(f"Running pipeline on {input_dir}...")
    results = pipeline.run_batch(input_dir, output_dir)
    
    for res in results:
        print(f"File: {res['file']}, Status: {res['status']}")
        if res['status'] == 'success':
            # Verify output content
            with open(res['output'], 'r') as f:
                data = json.load(f)
                # Check if we have some data
                if "basics" in data and "name" in data["basics"]:
                     print(f"  - Verified content: Found name '{data['basics']['name']}'")
                else:
                     print(f"  - Warning: Content might be empty or malformed.")

if __name__ == "__main__":
    main()
