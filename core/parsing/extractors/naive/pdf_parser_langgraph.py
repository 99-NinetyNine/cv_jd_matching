from typing import Dict, Any, Union, Optional, TypedDict, Annotated
from pathlib import Path
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException
from core.parsing.extractors.base import BaseParser
from core.parsing.schema import Resume, Basics, Work, Education, Skill
from core.llm.factory import get_llm
import logging
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
from langdetect import detect, LangDetectException
from langgraph.graph import StateGraph, END
import operator

logger = logging.getLogger(__name__)


# State for LangGraph
class ParsingState(TypedDict):
    """State for the parsing workflow"""
    file_path: str
    raw_text: str
    is_scanned: bool
    validation_passed: bool
    error: Optional[str]

    # Chain of Thought fields
    text_extraction_reasoning: str
    validation_reasoning: str

    # Parallel extraction results
    basics_data: Optional[Dict[str, Any]]
    work_data: Optional[list]
    education_data: Optional[list]
    skills_data: Optional[list]

    # Final result
    parsed_resume: Optional[Dict[str, Any]]


class PDFParserLangGraph(BaseParser):
    """
    LangGraph-based PDF parser with:
    1. Chain of Thought (CoT) reasoning at each step
    2. Parallelization of section extraction
    3. State management via LangGraph
    """

    def __init__(self):
        self.llm = get_llm(temperature=0)
        self.workflow = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow with parallel extraction"""
        workflow = StateGraph(ParsingState)

        # Step 1: Text Extraction (with CoT)
        workflow.add_node("extract_text", self._extract_text_node)

        # Step 2: Validate extracted text (with CoT)
        workflow.add_node("validate_text", self._validate_text_node)

        # Step 3: Parallel extraction nodes
        workflow.add_node("extract_basics", self._extract_basics_node)
        workflow.add_node("extract_work", self._extract_work_node)
        workflow.add_node("extract_education", self._extract_education_node)
        workflow.add_node("extract_skills", self._extract_skills_node)

        # Step 4: Combine results
        workflow.add_node("combine_results", self._combine_results_node)

        # Define edges
        workflow.set_entry_point("extract_text")
        workflow.add_edge("extract_text", "validate_text")

        # Conditional routing after validation
        workflow.add_conditional_edges(
            "validate_text",
            self._should_continue_extraction,
            {
                "continue": "extract_basics",
                "error": END
            }
        )

        # Parallel extraction - all start after basics
        workflow.add_edge("extract_basics", "extract_work")
        workflow.add_edge("extract_basics", "extract_education")
        workflow.add_edge("extract_basics", "extract_skills")

        # All parallel nodes converge to combine
        workflow.add_edge("extract_work", "combine_results")
        workflow.add_edge("extract_education", "combine_results")
        workflow.add_edge("extract_skills", "combine_results")

        workflow.add_edge("combine_results", END)

        return workflow.compile()

    def _is_scanned_pdf(self, file_path: str) -> tuple[bool, str]:
        """
        Detect if PDF is scanned with Chain of Thought reasoning.

        Returns:
            (is_scanned, reasoning)
        """
        try:
            doc = fitz.open(file_path)
            total_text_len = 0
            num_pages = len(doc)

            if num_pages == 0:
                return False, "PDF has no pages, assuming not scanned"

            for page in doc:
                total_text_len += len(page.get_text().strip())

            doc.close()

            avg_text_per_page = total_text_len / num_pages
            is_scanned = avg_text_per_page < 50

            reasoning = (
                f"Analyzed {num_pages} pages with average {avg_text_per_page:.1f} chars/page. "
                f"Threshold is 50 chars/page. "
                f"Conclusion: {'SCANNED (image-based)' if is_scanned else 'NATIVE (text-based)'}"
            )

            logger.info(reasoning)
            return is_scanned, reasoning

        except Exception as e:
            reasoning = f"Failed to analyze PDF structure: {e}. Assuming native PDF."
            logger.warning(reasoning)
            return False, reasoning

    def _ocr_extract(self, file_path: str) -> str:
        """Extract text using OCR (Tesseract)"""
        logger.info("Starting OCR extraction...")
        try:
            images = convert_from_path(file_path)
            text = ""
            for i, img in enumerate(images):
                logger.info(f"OCR processing page {i+1}/{len(images)}")
                text += pytesseract.image_to_string(img) + "\n"
            return text
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            raise ValueError("OCR extraction failed. Ensure tesseract-ocr and poppler-utils are installed.")

    def _extract_text_node(self, state: ParsingState) -> ParsingState:
        """
        Node 1: Extract text with Chain of Thought reasoning
        """
        file_path = state["file_path"]

        # Step 1: Check if scanned
        is_scanned, scan_reasoning = self._is_scanned_pdf(file_path)

        # Step 2: Extract based on type
        if is_scanned:
            extraction_method = "OCR (Tesseract)"
            text = self._ocr_extract(file_path)
        else:
            extraction_method = "Native PyMuPDF"
            try:
                from langchain_community.document_loaders import PyMuPDFLoader
                loader = PyMuPDFLoader(file_path)
                docs = loader.load()
                text = "\n".join([doc.page_content for doc in docs])

                # Fallback to OCR if native extraction yields too little
                if len(text.strip()) < 50:
                    extraction_method = "Native->OCR Fallback"
                    text = self._ocr_extract(file_path)
            except Exception as e:
                extraction_method = f"Native failed ({e}), using Unstructured"
                from langchain_community.document_loaders import UnstructuredPDFLoader
                loader = UnstructuredPDFLoader(file_path)
                docs = loader.load()
                text = "\n".join([doc.page_content for doc in docs])

        # Chain of Thought reasoning
        reasoning = (
            f"Step 1: Scanned detection - {scan_reasoning}\n"
            f"Step 2: Extraction method selected - {extraction_method}\n"
            f"Step 3: Extracted {len(text)} characters from PDF\n"
        )

        state["raw_text"] = text
        state["is_scanned"] = is_scanned
        state["text_extraction_reasoning"] = reasoning

        logger.info(f"Text extraction CoT:\n{reasoning}")
        return state

    def _validate_text_node(self, state: ParsingState) -> ParsingState:
        """
        Node 2: Validate extracted text with Chain of Thought
        """
        text = state["raw_text"]

        # Validation checks with reasoning
        checks = []

        # Check 1: Length validation
        if len(text) < 50:
            checks.append(f"❌ Text too short ({len(text)} < 50 chars)")
            state["error"] = "Extracted text is too short"
            state["validation_passed"] = False
        elif len(text) > 100000:
            checks.append(f"❌ Text too long ({len(text)} > 100000 chars)")
            state["error"] = "Extracted text is too long"
            state["validation_passed"] = False
        else:
            checks.append(f"✓ Length valid ({len(text)} chars)")

        # Check 2: Language detection
        try:
            lang = detect(text[:1000])
            allowed_langs = ['en', 'es', 'fr', 'de']
            if lang in allowed_langs:
                checks.append(f"✓ Language detected: {lang} (allowed)")
            else:
                checks.append(f"⚠ Language detected: {lang} (not in allowed list, proceeding)")
        except LangDetectException:
            checks.append("⚠ Language detection failed (proceeding anyway)")

        # Final validation result
        if "error" not in state or state["error"] is None:
            state["validation_passed"] = True
            checks.append("✓ All validations passed")

        reasoning = "Validation checks:\n" + "\n".join(f"  {c}" for c in checks)
        state["validation_reasoning"] = reasoning

        logger.info(f"Validation CoT:\n{reasoning}")
        return state

    def _should_continue_extraction(self, state: ParsingState) -> str:
        """Conditional edge: continue or stop"""
        return "continue" if state.get("validation_passed", False) else "error"

    def _extract_basics_node(self, state: ParsingState) -> ParsingState:
        """
        Node 3a: Extract basics section using LLM
        """
        text = state["raw_text"]

        prompt = PromptTemplate(
            template="""You are an expert CV parser. Extract ONLY the basics/personal information from the CV.

Think step by step:
1. Identify name, email, phone, location
2. Extract professional summary/objective
3. Find social profiles (LinkedIn, GitHub, etc.)

CV Text:
{cv_text}

Return a JSON object following the Basics schema with fields:
- name, label, email, phone, url, summary, location, profiles

{format_instructions}
""",
            input_variables=["cv_text"],
            partial_variables={"format_instructions": "Return valid JSON only"}
        )

        try:
            llm_structured = self.llm.with_structured_output(Basics)
            chain = prompt | llm_structured
            basics = chain.invoke({"cv_text": text[:3000]})  # Use first 3k chars
            state["basics_data"] = basics.model_dump(exclude_none=True)
            logger.info(f"✓ Basics extracted: {basics.name}")
        except Exception as e:
            logger.error(f"Basics extraction failed: {e}")
            state["basics_data"] = {}

        return state

    def _extract_work_node(self, state: ParsingState) -> ParsingState:
        """
        Node 3b: Extract work experience (parallel)
        """
        text = state["raw_text"]

        prompt = PromptTemplate(
            template="""You are an expert CV parser. Extract ONLY work experience entries.

Think step by step:
1. Identify all employment/work sections
2. For each job, extract: company, position, dates, responsibilities
3. Structure as a list

CV Text:
{cv_text}

Return a JSON array of work experience objects.

{format_instructions}
""",
            input_variables=["cv_text"],
            partial_variables={"format_instructions": "Return valid JSON array"}
        )

        try:
            from pydantic import TypeAdapter
            llm_structured = self.llm.with_structured_output(TypeAdapter(list[Work]))
            chain = prompt | llm_structured
            work = chain.invoke({"cv_text": text})
            state["work_data"] = [w.model_dump(exclude_none=True) for w in work] if work else []
            logger.info(f"✓ Work extracted: {len(state['work_data'])} entries")
        except Exception as e:
            logger.error(f"Work extraction failed: {e}")
            state["work_data"] = []

        return state

    def _extract_education_node(self, state: ParsingState) -> ParsingState:
        """
        Node 3c: Extract education (parallel)
        """
        text = state["raw_text"]

        prompt = PromptTemplate(
            template="""You are an expert CV parser. Extract ONLY education history.

Think step by step:
1. Find all education/academic sections
2. For each entry, extract: institution, degree, field, dates
3. Structure as a list

CV Text:
{cv_text}

Return a JSON array of education objects.

{format_instructions}
""",
            input_variables=["cv_text"],
            partial_variables={"format_instructions": "Return valid JSON array"}
        )

        try:
            from pydantic import TypeAdapter
            llm_structured = self.llm.with_structured_output(TypeAdapter(list[Education]))
            chain = prompt | llm_structured
            education = chain.invoke({"cv_text": text})
            state["education_data"] = [e.model_dump(exclude_none=True) for e in education] if education else []
            logger.info(f"✓ Education extracted: {len(state['education_data'])} entries")
        except Exception as e:
            logger.error(f"Education extraction failed: {e}")
            state["education_data"] = []

        return state

    def _extract_skills_node(self, state: ParsingState) -> ParsingState:
        """
        Node 3d: Extract skills (parallel)
        """
        text = state["raw_text"]

        prompt = PromptTemplate(
            template="""You are an expert CV parser. Extract ONLY skills.

Think step by step:
1. Find skills sections (technical, soft skills, languages, tools)
2. Extract skill names and proficiency levels if mentioned
3. Structure as a list

CV Text:
{cv_text}

Return a JSON array of skill objects.

{format_instructions}
""",
            input_variables=["cv_text"],
            partial_variables={"format_instructions": "Return valid JSON array"}
        )

        try:
            from pydantic import TypeAdapter
            llm_structured = self.llm.with_structured_output(TypeAdapter(list[Skill]))
            chain = prompt | llm_structured
            skills = chain.invoke({"cv_text": text})
            state["skills_data"] = [s.model_dump(exclude_none=True) for s in skills] if skills else []
            logger.info(f"✓ Skills extracted: {len(state['skills_data'])} entries")
        except Exception as e:
            logger.error(f"Skills extraction failed: {e}")
            state["skills_data"] = []

        return state

    def _combine_results_node(self, state: ParsingState) -> ParsingState:
        """
        Node 4: Combine all parallel extraction results
        """
        parsed_resume = {
            "basics": state.get("basics_data", {}),
            "work": state.get("work_data", []),
            "education": state.get("education_data", []),
            "skills": state.get("skills_data", []),
            # Add other sections with empty defaults
            "volunteer": [],
            "awards": [],
            "certificates": [],
            "publications": [],
            "languages": [],
            "interests": [],
            "references": [],
            "projects": []
        }

        state["parsed_resume"] = parsed_resume
        logger.info("✓ All sections combined into final resume")
        return state

    def parse(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Main entry point for parsing with LangGraph workflow
        """
        initial_state: ParsingState = {
            "file_path": str(file_path),
            "raw_text": "",
            "is_scanned": False,
            "validation_passed": False,
            "error": None,
            "text_extraction_reasoning": "",
            "validation_reasoning": "",
            "basics_data": None,
            "work_data": None,
            "education_data": None,
            "skills_data": None,
            "parsed_resume": None
        }

        try:
            # Execute the workflow
            final_state = self.workflow.invoke(initial_state)

            # Check for errors
            if final_state.get("error"):
                return {"error": final_state["error"]}

            # Return parsed resume
            return final_state.get("parsed_resume", {"error": "Parsing failed"})

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return {"error": f"Parsing failed: {str(e)}"}
