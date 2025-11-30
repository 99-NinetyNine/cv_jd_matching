from scripts.process_external_data import ExternalDataProcessor
import os

def main():
    input_dir = "data/synthetic_verification"
    output_dir = "data/processed_external_test"
    
    if not os.path.exists(input_dir):
        print(f"Input directory {input_dir} does not exist. Run verify_generator.py first.")
        return

    processor = ExternalDataProcessor()
    print(f"Processing PDFs from {input_dir} to {output_dir}...")
    processor.process_directory(input_dir, output_dir)
    
    # Check results
    processed_count = 0
    for f in os.listdir(output_dir):
        if f.endswith(".json"):
            processed_count += 1
            
    print(f"Successfully processed {processed_count} files.")

if __name__ == "__main__":
    main()
