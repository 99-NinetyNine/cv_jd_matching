from typing import List, Dict
from core.llm.factory import get_llm
from langchain_core.prompts import PromptTemplate
import json
import random

class DataGenerator:
    def __init__(self):
        self.llm = get_llm()
        
    def generate_cvs(self, count: int = 5) -> List[Dict]:
        prompt = PromptTemplate(
            template="""Generate {count} synthetic CVs in JSON format.
            Each CV should have: name, summary, skills (list), work (list of companies/roles).
            Make them diverse (different roles like AI Engineer, Web Dev, Data Scientist).
            Return ONLY a JSON list.
            """,
            input_variables=["count"]
        )
        chain = prompt | self.llm
        try:
            result = chain.invoke({"count": count}).content
            # Simple cleanup to ensure JSON
            start = result.find("[")
            end = result.rfind("]") + 1
            return json.loads(result[start:end])
        except Exception as e:
            print(f"Error generating CVs: {e}")
            return []

    def generate_jobs(self, count: int = 5) -> List[Dict]:
        prompt = PromptTemplate(
            template="""Generate {count} synthetic Job Descriptions in JSON format.
            Each Job should have: job_id, title, company, description.
            Make them diverse.
            Return ONLY a JSON list.
            """,
            input_variables=["count"]
        )
        chain = prompt | self.llm
        try:
            result = chain.invoke({"count": count}).content
            start = result.find("[")
            end = result.rfind("]") + 1
            return json.loads(result[start:end])
        except Exception as e:
            print(f"Error generating Jobs: {e}")
            return []
