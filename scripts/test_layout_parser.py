from core.parsing.layout_parser import LayoutParser
import os

def main():
    parser = LayoutParser()
    pdf_path = "data/synthetic_verification/resume_0.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"File {pdf_path} not found. Run verify_generator.py first.")
        return

    print(f"Linearizing {pdf_path}...")
    linearized_text = parser.linearize_content(pdf_path)
    
    print("--- Linearized Content Sample (First 20 lines) ---")
    lines = linearized_text.split("\n")
    for line in lines[:20]:
        print(line)
    print("------------------------------------------------")
    
    # Basic check
    if "[0]" in linearized_text:
        print("SUCCESS: Index markers found.")
    else:
        print("FAILED: No index markers found.")

if __name__ == "__main__":
    main()
