from typing import Dict, Any, Union, Optional
from pathlib import Path
from langchain_community.document_loaders import PyMuPDFLoader, UnstructuredPDFLoader
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException
from core.parsing.extractors.base import BaseParser
from core.parsing.schema import Resume
from core.llm.factory import get_llm
import logging
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)

class PDFParser(BaseParser):
    def __init__(self):
        self.llm = get_llm(temperature=0)
        self.parser = PydanticOutputParser(pydantic_object=Resume)
        
    def _is_scanned_pdf(self, file_path: str) -> bool:
        """
        Detect if PDF is likely scanned (image-based) by checking text density.
        Heuristic: If average text characters per page < 50, assume scanned.
        """
        try:
            doc = fitz.open(file_path)
            total_text_len = 0
            num_pages = len(doc)
            
            if num_pages == 0:
                return False
                
            for page in doc:
                total_text_len += len(page.get_text().strip())
            
            doc.close()
            
            avg_text_per_page = total_text_len / num_pages
            logger.info(f"Average text per page: {avg_text_per_page}")
            
            return avg_text_per_page < 50
        except Exception as e:
            logger.warning(f"Failed to check if scanned: {e}")
            return False

    def _ocr_extract(self, file_path: str) -> str:
        """Extract text using OCR (Tesseract) via pdf2image."""
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

    def _extract_text(self, file_path: str) -> str:
        """Extract text with robust fallback strategy: Native -> OCR -> Unstructured."""
        # 1. Validation Checks
        try:
            doc = fitz.open(file_path)
            if doc.page_count > 10:
                raise ValueError(f"PDF has too many pages ({doc.page_count}). Maximum is 10.")
            doc.close()
        except Exception as e:
            logger.warning(f"Pre-validation failed: {e}")

        # 2. Check for Scanned PDF
        if self._is_scanned_pdf(file_path):
            logger.info("Detected scanned PDF. Attempting OCR...")
            return self._ocr_extract(file_path)

        # 3. Native Extraction (PyMuPDF)
        try:
            loader = PyMuPDFLoader(file_path)
            docs = loader.load()
            text = "\n".join([doc.page_content for doc in docs])
            
            # Double check length after extraction
            if len(text.strip()) < 50:
                logger.info("Native extraction yielded too little text. Trying OCR...")
                return self._ocr_extract(file_path)
                
            return text
        except Exception as e:
            logger.warning(f"Native extraction failed: {e}. Trying Unstructured...")
            
        # 4. Fallback: Unstructured
        try:
            loader = UnstructuredPDFLoader(file_path)
            docs = loader.load()
            return "\n".join([doc.page_content for doc in docs])
        except Exception as e:
            raise ValueError(f"All extraction methods failed for {file_path}: {e}")

    def _validate_content(self, text: str):
        """Validate extracted content."""
        if len(text) < 50:
            raise ValueError("Extracted text is too short.")
        if len(text) > 100000:
            raise ValueError("Extracted text is too long.")
            
        try:
            lang = detect(text[:1000])
            allowed_langs = ['en', 'es', 'fr', 'de']
            if lang not in allowed_langs:
                logger.warning(f"Detected language '{lang}' not in allowed list. Proceeding anyway.")
        except LangDetectException:
            pass

    def parse(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        file_path = str(file_path)
        
        # 1. Extract Text
        try:
            full_text = self._extract_text(file_path)
            self._validate_content(full_text)
        except ValueError as e:
            return {"error": str(e)}
            
        # 2. Hybrid Extraction: Regex Rules (High Confidence)
        # This did not work perfectly, so it can be removed..
        # regex_data = {
        #     "email": RegexRules.extract_emails(full_text),
        #     "phone": RegexRules.extract_phones(full_text),
        #     "links": RegexRules.extract_links(full_text),
        #     # "dates": RegexRules.extract_dates(full_text) # Can be noisy, use with care
        # }
        # return regex_data

        # 3. LLM Extraction
        prompt = PromptTemplate(
            template="""You are an expert CV parser. Extract structured info from the CV.
            
            CV Text:
            {cv_text}
            
            {format_instructions}
            """,
            input_variables=["cv_text"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )
        ##############
        import json
        with open("core/parsing/tests_data/resume_and_texts_kaggle/some/ADVOCATE_14445309.json", 'r') as f:
            return json.load(f)

        ##########
        chain = prompt | self.llm | self.parser
        
        try:
            resume_data = chain.invoke({"cv_text": full_text})
            parsed_dict = resume_data.model_dump()

            # any additional processing can be done here            
            return parsed_dict
            
        except OutputParserException as e:
            logger.error(f"Parsing error: {e}")
            return {"error": "Failed to parse LLM output", "details": "Please try again later."}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"error": "Something went wrong.Please try again later."}
