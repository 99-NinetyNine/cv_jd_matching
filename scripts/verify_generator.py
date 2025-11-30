from core.evaluation.generator import DataGenerator
import os

def main():
    generator = DataGenerator()
    output_dir = "data/synthetic_verification"
    print(f"Generating resumes in {output_dir}...")
    resumes = generator.generate_and_render(output_dir, count=2)
    print(f"Generated {len(resumes)} resumes.")
    
    # Verify files exist
    for i in range(2):
        json_path = os.path.join(output_dir, f"resume_{i}.json")
        pdf_path = os.path.join(output_dir, f"resume_{i}.pdf")
        
        if os.path.exists(json_path) and os.path.exists(pdf_path):
            print(f"Verified: {json_path} and {pdf_path} exist.")
        else:
            print(f"FAILED: Missing files for index {i}")

if __name__ == "__main__":
    main()
