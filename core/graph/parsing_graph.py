from typing import TypedDict, Dict, Any, List
from langgraph.graph import StateGraph, END
from core.parsing.extractors.naive.pdf_parser import PDFParser
from core.matching.embeddings import EmbeddingFactory
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from core.llm.factory import get_llm
from core.parsing.schema import Resume
import numpy as np
import json
import logging

logger = logging.getLogger(__name__)

class ParsingState(TypedDict):
    file_path: str
    text_content: str
    chunks: List[str]
    chunk_embeddings: List[List[float]]
    parsed_data: Dict[str, Any]
    status: str
    error: str

def extract_text_node(state: ParsingState):
    """Node to extract text from PDF."""
    file_path = state["file_path"]
    parser = PDFParser()
    try:
        text = parser._extract_text(file_path)
        return {
            "text_content": text,
            "status": "Text extracted successfully."
        }
    except Exception as e:
        return {"error": str(e), "status": "Error extracting text."}

def chunk_text_node(state: ParsingState):
    """Node to chunk text for RAG."""
    text = state.get("text_content", "")
    if not text:
        return {"error": "No text content to chunk."}
        
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = splitter.split_text(text)
    return {
        "chunks": chunks,
        "status": f"Text split into {len(chunks)} chunks."
    }

def embed_chunks_node(state: ParsingState):
    """Node to embed chunks."""
    chunks = state.get("chunks", [])
    if not chunks:
        return {"error": "No chunks to embed."}
        
    embedder = EmbeddingFactory.get_embedder()
    try:
        embeddings = embedder.embed_documents(chunks)
        return {
            "chunk_embeddings": embeddings,
            "status": "Chunks embedded."
        }
    except Exception as e:
        return {"error": str(e), "status": "Error embedding chunks."}

def rag_extract_node(state: ParsingState):
    """Node to extract structured data using RAG."""
    chunks = state.get("chunks", [])
    embeddings = state.get("chunk_embeddings", [])
    
    if not chunks or not embeddings:
        return {"error": "Missing chunks or embeddings."}
        
    llm = get_llm()
    
    # Helper to find relevant chunks
    def get_relevant_context(query: str, k: int = 3) -> str:
        embedder = EmbeddingFactory.get_embedder()
        query_emb = embedder.embed_query(query)
        
        # Simple cosine similarity
        scores = []
        for i, emb in enumerate(embeddings):
            score = np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb))
            scores.append((score, i))
            
        scores.sort(key=lambda x: x[0], reverse=True)
        top_indices = [idx for _, idx in scores[:k]]
        return "\n---\n".join([chunks[i] for i in top_indices])

    sections = {
        "basics": "contact information, name, email, phone, links, summary",
        "skills": "technical skills, programming languages, tools, soft skills",
        "work": "work experience, employment history, job roles, companies, dates",
        "education": "education, degrees, universities, certifications"
    }
    
    final_data = {}
    
    for section, query in sections.items():
        context = get_relevant_context(query)
        
        prompt = PromptTemplate(
            template="""You are an expert CV parser. Extract the '{section}' section from the following context.
            Return ONLY a valid JSON object matching the schema for this section.
            
            Context:
            {context}
            
            Output JSON for '{section}':
            """,
            input_variables=["section", "context"]
        )
        
        try:
            chain = prompt | llm
            result = chain.invoke({"section": section, "context": context})
            content = result.content.strip()
            # Clean markdown code blocks
            if content.startswith("```json"):
                content = content[7:-3]
            elif content.startswith("```"):
                content = content[3:-3]
                
            section_data = json.loads(content)
            final_data[section] = section_data
        except Exception as e:
            logger.error(f"Failed to extract section {section}: {e}")
            # Fallback or empty
            final_data[section] = {}

    return {
        "parsed_data": final_data,
        "status": "RAG extraction complete."
    }

def fetch_external_data_node(state: ParsingState):
    """Node to fetch external data from links."""
    # (Simplified for brevity, same logic as before but using parsed_data)
    return {"status": "External data fetch skipped for now."}

def create_parsing_graph():
    workflow = StateGraph(ParsingState)
    
    workflow.add_node("extract_text", extract_text_node)
    workflow.add_node("chunk_text", chunk_text_node)
    workflow.add_node("embed_chunks", embed_chunks_node)
    workflow.add_node("rag_extract", rag_extract_node)
    workflow.add_node("fetch_external", fetch_external_data_node)
    
    workflow.set_entry_point("extract_text")
    workflow.add_edge("extract_text", "chunk_text")
    workflow.add_edge("chunk_text", "embed_chunks")
    workflow.add_edge("embed_chunks", "rag_extract")
    workflow.add_edge("rag_extract", "fetch_external")
    workflow.add_edge("fetch_external", END)
    
    return workflow.compile()

