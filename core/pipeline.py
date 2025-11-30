from core.parsing.layout_parser import LayoutParser
from core.parsing.extractor import Extractor
from core.parsing.schema import Resume
from typing import Dict, Any
import os

class ResumeExtractionPipeline:
    def __init__(self):
        self.layout_parser = LayoutParser()
        self.extractor = Extractor()

    def process(self, pdf_path: str) -> Dict[str, Any]:
        """
        Run the full extraction pipeline on a PDF file.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"File not found: {pdf_path}")

        # 1. Layout Parsing & Linearization
        print(f"Linearizing content from {pdf_path}...")
        linearized_text = self.layout_parser.linearize_content(pdf_path)
        
        # Extract original lines for pointer resolution
        # Assuming format "[index] content"
        original_lines = []
        for line in linearized_text.split("\n"):
            if line.strip():
                if "] " in line:
                    original_lines.append(line.split("] ", 1)[1])
                else:
                    original_lines.append(line) # Fallback

        # 2. LLM Extraction
        print("Extracting structured data...")
        raw_data = self.extractor.extract_all(linearized_text)
        
        # 3. Post-Processing (Pointer Resolution)
        print("Resolving pointers...")
        resolved_data = self.extractor.resolve_pointers(raw_data, original_lines)
        
        # 4. Final Cleanup / Validation (Optional)
        # We could map resolved_data to the Resume Pydantic model to ensure validity
        # But for now, return the dict
        
        return resolved_data

    def run_batch(self, input_dir: str, output_dir: str):
        """
        Process all PDFs in a directory.
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
