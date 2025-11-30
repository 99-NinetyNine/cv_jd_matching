from typing import List, Dict, Any, Optional
from core.llm.factory import get_llm
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from core.parsing.schema import Resume, Basics, Work, Education, Skill, Project
import json
import concurrent.futures

class Extractor:
    """ This is based on https://arxiv.org/pdf/2510.09722"""
    def __init__(self):
        self.llm = get_llm()
        
    def _create_chain(self, pydantic_object):
        parser = JsonOutputParser(pydantic_object=pydantic_object)
        prompt = PromptTemplate(
            template="""Extract the following section from the resume text.
            The text is provided with line numbers in the format [index] content.
            
            For long text fields (like descriptions, summaries), DO NOT generate the text.
            Instead, return the line number range as a string "start_index-end_index" (e.g., "15-20").
            If it's a single line, just return the index (e.g., "15").
            
            RESUME TEXT:
            {text}
            
            {format_instructions}
            """,
            input_variables=["text"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        return prompt | self.llm | parser

    def extract_section(self, section_name: str, text: str, model_class):
        print(f"Extracting {section_name}...")
        chain = self._create_chain(model_class)
        try:
            result = chain.invoke({"text": text})
            # Robustness: If result is a dict and has the section name as key, unwrap it
            if isinstance(result, dict) and section_name in result:
                return result[section_name]
            return result
        except Exception as e:
            print(f"Error extracting {section_name}: {e}")
            return [] if section_name != "basics" else {}

    def extract_basics(self, text: str) -> Dict:
        return self.extract_section("basics", text, Basics)

    def extract_work(self, text: str) -> List[Dict]:
        parser = JsonOutputParser(pydantic_object=Work)
        prompt = PromptTemplate(
            template="""Extract the 'Work Experience' section from the resume text as a JSON LIST of objects.
            The text is provided with line numbers in the format [index] content.
            
            For 'summary' and 'highlights', return the line number range (e.g., "15-20") or index.
            
            RESUME TEXT:
            {text}
            
            Return a JSON list of Work objects.
            {format_instructions}
            """,
            input_variables=["text"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        chain = prompt | self.llm | parser
        try:
            result = chain.invoke({"text": text})
            if isinstance(result, dict) and "work" in result:
                return result["work"]
            return result
        except Exception as e:
            print(f"Error extracting work: {e}")
            return []

    def extract_education(self, text: str) -> List[Dict]:
        parser = JsonOutputParser(pydantic_object=Education)
        prompt = PromptTemplate(
            template="""Extract the 'Education' section from the resume text as a JSON LIST of objects.
            The text is provided with line numbers in the format [index] content.
            
            RESUME TEXT:
            {text}
            
            Return a JSON list of Education objects.
            {format_instructions}
            """,
            input_variables=["text"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        chain = prompt | self.llm | parser
        try:
            result = chain.invoke({"text": text})
            if isinstance(result, dict) and "education" in result:
                return result["education"]
            return result
        except Exception as e:
            print(f"Error extracting education: {e}")
            return []
            
    def extract_skills(self, text: str) -> List[Dict]:
        parser = JsonOutputParser(pydantic_object=Skill)
        prompt = PromptTemplate(
            template="""Extract the 'Skills' section from the resume text as a JSON LIST of objects.
            The text is provided with line numbers in the format [index] content.
            
            RESUME TEXT:
            {text}
            
            Return a JSON list of Skill objects.
            {format_instructions}
            """,
            input_variables=["text"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        chain = prompt | self.llm | parser
        try:
            result = chain.invoke({"text": text})
            if isinstance(result, dict) and "skills" in result:
                return result["skills"]
            return result
        except Exception as e:
            print(f"Error extracting skills: {e}")
            return []

    def extract_all(self, text: str) -> Dict:
        """
        Parallelized extraction of all sections.
        """
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_basics = executor.submit(self.extract_basics, text)
            future_work = executor.submit(self.extract_work, text)
            future_edu = executor.submit(self.extract_education, text)
            future_skills = executor.submit(self.extract_skills, text)
            
            results = {
                "basics": future_basics.result(),
                "work": future_work.result(),
                "education": future_edu.result(),
                "skills": future_skills.result(),
                # Add others as needed
            }
            
        return results

    def resolve_pointers(self, extracted_data: Dict, original_lines: List[str]) -> Dict:
        """
        Post-processing to resolve line number pointers to actual text.
        Recursively traverses the dictionary to find pointer fields.
        """
        def resolve_value(value):
            if isinstance(value, str):
                # Check if it looks like a pointer "15-20" or "15"
                # Simple heuristic: if it contains digits and maybe a hyphen, and is short
                if len(value) < 10 and any(c.isdigit() for c in value):
                    try:
                        if "-" in value:
                            start, end = map(int, value.split("-"))
                            # Ensure bounds
                            start = max(0, start)
                            end = min(len(original_lines), end + 1) # +1 because range is exclusive usually, but let's assume inclusive prompt
                            return " ".join(original_lines[start:end]).strip()
                        else:
                            idx = int(value)
                            if 0 <= idx < len(original_lines):
                                return original_lines[idx].strip()
                    except ValueError:
                        pass # Not a pointer
            elif isinstance(value, list):
                return [resolve_value(item) for item in value]
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            return value

        return resolve_value(extracted_data)
