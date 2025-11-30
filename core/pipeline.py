from core.parsing.main import RESUME_PARSER
from core.parsing.schema import Resume
from typing import Dict, Any
import os

class ResumeExtractionPipeline:
    """
    Simplified pipeline using the naive PDF parser.
    This uses a single-step LLM extraction instead of the multi-stage approach.
    """
    def __init__(self):
        self.parser = RESUME_PARSER

    def process(self, pdf_path: str) -> Dict[str, Any]:
        """
        Run the extraction pipeline on a PDF file using the naive parser.
        
        Args:
            pdf_path: Path to the PDF file to process
            
        Returns:
            Dictionary containing extracted resume data or error information
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"File not found: {pdf_path}")

        print(f"Processing {pdf_path}...")
        
        # Use the naive parser which handles everything in one step
        result = self.parser.parse(pdf_path)
        
        # Check if there was an error
        if "error" in result:
            print(f"Error processing {pdf_path}: {result['error']}")
        else:
            print(f"Successfully extracted data from {pdf_path}")
        
        return result

    def run_batch(self, input_dir: str, output_dir: str):
        """
        Process all PDFs in a directory.
        
        Args:
            input_dir: Directory containing PDF files
            output_dir: Directory to save JSON output files
            
        Returns:
            List of results with status for each file
        """
        os.makedirs(output_dir, exist_ok=True)
        
        results = []
        for filename in os.listdir(input_dir):
            if filename.lower().endswith(".pdf"):
                pdf_path = os.path.join(input_dir, filename)
                try:
                    data = self.process(pdf_path)
                    
                    output_filename = os.path.splitext(filename)[0] + ".json"
                    output_path = os.path.join(output_dir, output_filename)
                    
                    import json
                    with open(output_path, "w") as f:
                        json.dump(data, f, indent=2)
                        
                    results.append({"file": filename, "status": "success", "output": output_path})
                    print(f"Successfully processed {filename}")
                    
                except Exception as e:
                    print(f"Failed to process {filename}: {e}")
                    results.append({"file": filename, "status": "error", "error": str(e)})
                    
        return results
