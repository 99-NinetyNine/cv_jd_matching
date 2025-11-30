from core.parsing.extractors.naive.pdf_parser import PDFParser

# for now let's just use naive way to parse
# given pdf, ask llm in  single step to extract entire JSON
# reference architecture is optimal, takes less time and cost effective too, but needs to fine tune smaller LLMs
RESUME_PARSER = PDFParser() # Uses default model