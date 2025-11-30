import fitz  # PyMuPDF
from typing import List, Tuple, Dict, Any
import numpy as np
from PIL import Image
import io
"""
Todo: this is also based on https://arxiv.org/pdf/2510.09722 but since for YOLO to work we need to set up boundaries of the multiple-sections cv, so this
works only if resume cli allows pdf to be created along with dimensions of each sections.

This is a Future improvement.
"""
class LayoutParser:
    def __init__(self, model_path: str = None):
        self.model_path = model_path
        # self.model = YOLO(model_path) if model_path else None
        pass

    def render_pdf_to_images(self, pdf_path: str, dpi: int = 200) -> List[Image.Image]:
        """
        Render each page of the PDF to a PIL Image.
        """
        doc = fitz.open(pdf_path)
        images = []
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            images.append(img)
        return images

    def extract_layout(self, image: Image.Image) -> List[Dict[str, Any]]:
        """
        Detect layout segments (columns, sidebars) using YOLO.
        Returns a list of bounding boxes with labels.
        """
        if self.model_path:
            from ultralytics import YOLO
            if not hasattr(self, 'model') or self.model is None:
                self.model = YOLO(self.model_path)
            
            # Inference
            results = self.model(image)
            blocks = []
            for r in results:
                for box in r.boxes:
                    b = box.xyxy[0].tolist() # x1, y1, x2, y2
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    label = self.model.names[cls]
                    blocks.append({
                        "label": label,
                        "box": b,
                        "confidence": conf
                    })
            return blocks
        
        # Fallback: return a single block covering the whole image (linear layout assumption)
        width, height = image.size
        return [{
            "label": "main_content",
            "box": [0, 0, width, height],
            "confidence": 1.0
        }]

    def extract_text_blocks(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract text blocks with coordinates from PDF metadata.
        """
        doc = fitz.open(pdf_path)
        blocks = []
        for page_num, page in enumerate(doc):
            # get_text("dict") returns blocks with bbox and text
            page_dict = page.get_text("dict")
            for block in page_dict.get("blocks", []):
                if block["type"] == 0:  # Text block
                    for line in block["lines"]:
                        for span in line["spans"]:
                            blocks.append({
                                "page": page_num,
                                "text": span["text"],
                                "bbox": span["bbox"], # (x0, y0, x1, y1)
                                "size": span["size"],
                                "font": span["font"]
                            })
        return blocks

    def linearize_content(self, pdf_path: str) -> str:
        """
        Main method to produce linearized, indexed text.
        Combines layout analysis and text extraction.
        """
        # 1. Render images (for layout analysis)
        images = self.render_pdf_to_images(pdf_path)
        
        # 2. Extract raw text blocks with coordinates
        raw_blocks = self.extract_text_blocks(pdf_path)
        
        # 3. Perform Layout Analysis (per page)
        # For now, we assume simple top-down, but we will implement sorting here.
        
        # Sort blocks: Primary sort by Page, then Y (top-down), then X (left-right)
        # This is a naive "reading order" sort.
        # TODO: Implement sophisticated inter-segment sorting using layout boxes.
        
        sorted_blocks = sorted(raw_blocks, key=lambda b: (b["page"], b["bbox"][1], b["bbox"][0]))
        
        linearized_text = ""
        for i, block in enumerate(sorted_blocks):
            text = block["text"].strip()
            if text:
                linearized_text += f"[{i}] {text}\n"
                
        return linearized_text
