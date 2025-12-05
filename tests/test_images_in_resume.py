import sys
import os
import json
import glob
from pathlib import Path
from typing import Dict, Any

# Add the parent directory to sys.path to allow importing from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.parsing.extractors.naive import pdf_parser

# Test 1
# print(pdf_parser.PDFParser()._is_scanned_pdf("tests/cv_edge_cases/cv_with_a_image.pdf"))
# False
# print(pdf_parser.PDFParser()._ocr_extract("tests/cv_edge_cases/cv_with_a_image.pdf"))
# Java was extracted

# Test 2
print(pdf_parser.PDFParser()._is_scanned_pdf("tests/cv_edge_cases/cv_with_image_details.pdf"))
# False
print(pdf_parser.PDFParser()._ocr_extract("tests/cv_edge_cases/cv_with_image_details.pdf"))
""" predicted:
Artificial Intelligence and Machine Learning

APACHE

Spark co Scaea TNEANO

F TensorFlow Bl kersqfan
CNTK PYTORCH s<¢x2
"""
