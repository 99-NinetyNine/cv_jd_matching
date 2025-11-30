from typing import List, Dict
from core.llm.factory import get_llm
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from core.parsing.schema import Resume
from core.evaluation.renderer import PDFRenderer
import json
import os

class DataGenerator:
    def __init__(self):
        self.llm = get_llm()
        self.renderer = PDFRenderer()
        self.parser = PydanticOutputParser(pydantic_object=Resume)
        
    def generate_cvs(self, count: int = 5) -> List[Resume]:
        # We generate one by one for better quality/adherence to schema
        resumes = []
        
        prompt = PromptTemplate(
            template="""Generate a synthetic Resume in JSON format.
            Make it realistic and diverse.
            {format_instructions}
            """,
            input_variables=[],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
        
        chain = prompt | self.llm | self.parser
        
        for _ in range(count):
            try:
                resume = chain.invoke({})
                resumes.append(resume)
            except Exception as e:
                print(f"Error generating CV: {e}")
                
        return resumes

    def generate_and_render(self, output_dir: str, count: int = 5):
        os.makedirs(output_dir, exist_ok=True)
        resumes = self.generate_cvs(count)
        
        for i, resume in enumerate(resumes):
            # Save JSON
            json_path = os.path.join(output_dir, f"resume_{i}.json")
            with open(json_path, "w") as f:
                f.write(resume.model_dump_json(indent=2))
            
            # Render PDF
            pdf_path = os.path.join(output_dir, f"resume_{i}.pdf")
            self.renderer.render(resume, pdf_path)
            
        return resumes
