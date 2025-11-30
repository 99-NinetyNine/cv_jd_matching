from core.parsing.extractor import Extractor
from core.parsing.layout_parser import LayoutParser
import os
import json

def main():
    # 1. Linearize
    layout_parser = LayoutParser()
    pdf_path = "data/synthetic_verification/resume_0.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"File {pdf_path} not found.")
        return

    print(f"Linearizing {pdf_path}...")
    linearized_text = layout_parser.linearize_content(pdf_path)
    original_lines = [line.split("] ", 1)[1] if "] " in line else line for line in linearized_text.split("\n") if line]
    
    # 2. Extract
    extractor = Extractor()
    print("Extracting data (using mock LLM)...")
    
    # We need to mock the LLM response to return pointers for this test to be meaningful
    # But since we are using the 'mock' LLM from factory which returns fixed JSON without pointers,
    # we might not see the pointer resolution in action unless we change the mock data.
    # However, we can test the mechanics.
    
    data = extractor.extract_all(linearized_text)
    
    print("--- Extracted Data (Raw) ---")
    print(json.dumps(data, indent=2))
    
    # 3. Resolve Pointers (Mock test)
    # Let's manually inject some pointers to test resolution
    data["work"][0]["summary"] = "2-3" # Should map to lines 2 and 3 of linearized text
    
    print("--- Resolving Pointers ---")
    resolved_data = extractor.resolve_pointers(data, original_lines)
    
    print(json.dumps(resolved_data, indent=2))
    
    if resolved_data["work"][0]["summary"] != "2-3":
         print("SUCCESS: Pointer resolved.")
    else:
         print("FAILED: Pointer not resolved.")

if __name__ == "__main__":
    main()
