import os
import json
from typing import List, Optional
from core.llm.factory import get_llm
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from core.parsing.schema import Resume
import pymupdf

class ExternalDataProcessor:
    def __init__(self):
        self.llm = get_llm()
        self.parser = PydanticOutputParser(pydantic_object=Resume)
        
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        try:
            doc = pymupdf.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            return text
        except Exception as e:
            print(f"Error reading PDF {pdf_path}: {e}")
            return ""

    def convert_to_json(self, text: str) -> Optional[Resume]:
        prompt = PromptTemplate(
            template="""Extract the following resume text into a structured JSON object following the schema.
            If information is missing, leave fields null or empty.
            
            RESUME TEXT:
            {text}
            
            {format_instructions}
            """,
            input_variables=["text"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
        
        chain = prompt | self.llm | self.parser
        
        try:
            return chain.invoke({"text": text})
        except Exception as e:
            print(f"Error converting text to JSON: {e}")
            return None

    def process_directory(self, input_dir: str, output_dir: str):
        os.makedirs(output_dir, exist_ok=True)
        
        for filename in os.listdir(input_dir):
            if filename.lower().endswith(".pdf"):
                pdf_path = os.path.join(input_dir, filename)
                print(f"Processing {filename}...")
                
                text = self.extract_text_from_pdf(pdf_path)
                if not text.strip():
                    print(f"Skipping empty text for {filename}")
                    continue
                    
                resume = self.convert_to_json(text)
                if resume:
                    output_filename = os.path.splitext(filename)[0] + ".json"
                    output_path = os.path.join(output_dir, output_filename)
                    with open(output_path, "w") as f:
                        f.write(resume.model_dump_json(indent=2))
                    print(f"Saved {output_path}")
                else:
                    print(f"Failed to extract JSON for {filename}")

if __name__ == "__main__":
    # Example usage
    # processor = ExternalDataProcessor()
    # processor.process_directory("data/kaggle_raw", "data/processed_json")
    pass
