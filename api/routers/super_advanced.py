"""
🔥 ULTIMATE UNIFIED CV ANALYSIS SYSTEM 🔥

Consolidates ALL best features from:
- candidate.py (parsing, embedding, matching)
- advanced_candidate.py (quality scoring, explainability - BEST PROMPTS!)
- cv_quality.py (detailed quality with token streaming)

ONE WebSocket, ALL features, ELEGANT & EFFICIENT!
"""

from fastapi import APIRouter, WebSocket, Depends, UploadFile, File, HTTPException
from sqlmodel import Session, select
from typing import Dict, Any, List, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from pathlib import Path
import json
import logging
import asyncio
import psycopg2
import os
import uuid

from core.db.engine import get_session
from core.db.models import CV, Job, Prediction, User
from core.llm.factory import get_llm
from core.configs import USE_REAL_LLM
from core.parsing.main import RESUME_PARSER as parse_cv
from core.matching.embeddings import EmbeddingFactory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/super-advanced", tags=["super-advanced"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# State for LangGraph
class SuperState(TypedDict):
    cv_id: str
    cv_file_path: str
    is_premium: bool
    user_wants_quality_check: bool
    cv_data: Dict[str, Any]
    cv_text: str
    quality_scores: Dict[str, Any]
    cv_embedding: List[float]
    top_matches: List[Dict[str, Any]]
    contrastive_explanation: str
    counterfactual_suggestions: List[str]
    cot_reasoning: str
    current_node: str
    error: str


class UltimatePipeline:
    def __init__(self):
        self.llm = get_llm()
        self.embedder = EmbeddingFactory.get_embedder(provider="ollama")
        self.db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/cv_matching")
        self.app = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(SuperState)
        workflow.add_node("parse", self.parse_cv)
        workflow.add_node("quality", self.quality_check)
        workflow.add_node("embed", self.embed_cv)
        workflow.add_node("search", self.vector_search)
        workflow.add_node("contrastive", self.explain_contrastive)
        workflow.add_node("counterfactual", self.suggest_counterfactual)
        workflow.add_node("cot", self.cot_reasoning)

        workflow.set_entry_point("parse")
        workflow.add_conditional_edges(
            "parse",
            lambda s: "quality" if s.get("user_wants_quality_check") else "skip",
            {"quality": "quality", "skip": "embed"}
        )
        workflow.add_edge("quality", "embed")
        workflow.add_edge("embed", "search")
        workflow.add_edge("search", "contrastive")
        workflow.add_edge("contrastive", "counterfactual")
        workflow.add_edge("counterfactual", "cot")
        workflow.add_edge("cot", END)

        return workflow.compile(checkpointer=MemorySaver())

    def parse_cv(self, state: SuperState):
        cv_data = parse_cv.parse(state["cv_file_path"])
        basics = cv_data.get("basics", {})
        skills = cv_data.get("skills", [])
        cv_text = f"Name: {basics.get('name')}\nSkills: {', '.join([s.get('name', '') for s in skills[:10]])}"
        return {"cv_data": cv_data, "cv_text": cv_text, "current_node": "parse"}

    def quality_check(self, state: SuperState):
        cv_data = state["cv_data"]
        basics = cv_data.get("basics", {})
        work = cv_data.get("work", [])
        skills = cv_data.get("skills", [])

        score = 100
        issues = []
        if not basics.get("email"): score -= 15; issues.append("Missing email")
        if not basics.get("phone"): score -= 10; issues.append("Missing phone")
        if not work: score -= 25; issues.append("No work experience")
        if not skills: score -= 15; issues.append("No skills")

        return {
            "quality_scores": {"overall_score": score, "issues": issues},
            "current_node": "quality"
        }

    def embed_cv(self, state: SuperState):
        embedding = self.embedder.embed_query(state["cv_text"])
        return {"cv_embedding": embedding, "current_node": "embed"}

    def vector_search(self, state: SuperState):
        embedding = state["cv_embedding"]
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor()
        cur.execute("""
            SELECT job_id, canonical_json, 1 - (embedding <=> %s::vector) as similarity
            FROM job WHERE embedding_status = 'completed'
            ORDER BY embedding <=> %s::vector LIMIT 2;
        """, (embedding, embedding))

        matches = []
        for row in cur.fetchall():
            job_data = row[1]
            matches.append({
                "job_id": row[0],
                "data": job_data,
                "title": job_data.get("title"),
                "company": job_data.get("company"),
                "match_score": float(row[2])
            })
        cur.close()
        conn.close()

        return {"top_matches": matches, "current_node": "search"}

    def explain_contrastive(self, state: SuperState):
        matches = state["top_matches"]
        if len(matches) < 2:
            return {"contrastive_explanation": "Only one match.", "current_node": "contrastive"}

        job_a, job_b = matches[0], matches[1]
        prompt = f"""Why is Job A ranked higher?

CANDIDATE: {state['cv_text'][:500]}

JOB A: {job_a['title']} ({job_a['match_score']:.0%})
JOB B: {job_b['title']} ({job_b['match_score']:.0%})

Explain in 3 sentences."""

        explanation = self.llm.invoke(prompt).content if USE_REAL_LLM else f"Job A better matches skills."
        return {"contrastive_explanation": explanation, "current_node": "contrastive"}

    def suggest_counterfactual(self, state: SuperState):
        top = state["top_matches"][0] if state["top_matches"] else None
        if not top:
            return {"counterfactual_suggestions": [], "current_node": "counterfactual"}

        prompt = f"""3 'what-if' suggestions for {top['title']} (current: {top['match_score']:.0%})

Format: "If you [change], score improves from X to Y"
Return JSON list."""

        if USE_REAL_LLM:
            try:
                suggestions = json.loads(self.llm.invoke(prompt).content)
            except:
                suggestions = ["Add certifications to improve 10%"]
        else:
            suggestions = [f"Add skills to reach 85%", "Quantify achievements +5-10%"]

        return {"counterfactual_suggestions": suggestions, "current_node": "counterfactual"}

    def cot_reasoning(self, state: SuperState):
        top = state["top_matches"][0] if state["top_matches"] else None
        if not top:
            return {"cot_reasoning": "No matches", "current_node": "cot"}

        prompt = f"""Step-by-step reasoning for {top['title']} match:

CANDIDATE: {state['cv_text'][:500]}
MATCH: {top['match_score']:.0%}

Step 1: Skills?
Step 2: Experience?
Step 3: Fit?
Step 4: Decision?"""

        reasoning = self.llm.invoke(prompt).content if USE_REAL_LLM else "Strong match based on skills."
        return {"cot_reasoning": reasoning, "current_node": "cot"}


# WebSocket
@router.websocket("/ws/analyze/{cv_id}")
async def ultimate_ws(websocket: WebSocket, cv_id: str, session: Session = Depends(get_session)):
    await websocket.accept()
    try:
        file_path = UPLOAD_DIR / f"{cv_id}.pdf"
        if not file_path.exists():
            await websocket.send_json({"event": "error", "message": "File not found"})
            return

        await websocket.send_json({"event": "user_choice", "message": "Want quality check?", "choices": ["yes", "no"]})
        try:
            user_msg = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
            wants_quality = user_msg.get("choice") == "yes"
        except:
            wants_quality = False

        pipeline = UltimatePipeline()
        state = {
            "cv_id": cv_id,
            "cv_file_path": str(file_path),
            "is_premium": True,
            "user_wants_quality_check": wants_quality,
            "cv_data": {}, "cv_text": "", "quality_scores": {},
            "cv_embedding": [], "top_matches": [],
            "contrastive_explanation": "", "counterfactual_suggestions": [], "cot_reasoning": "",
            "current_node": "", "error": ""
        }

        async for event in pipeline.app.astream(state, {"configurable": {"thread_id": cv_id}}):
            for node_name, state_update in event.items():
                await websocket.send_json({"event": "node_start", "node": node_name})

                # Token streaming for quality
                if node_name == "quality" and wants_quality:
                    await websocket.send_json({"event": "quality_scores", "data": state_update.get("quality_scores")})
                    if USE_REAL_LLM:
                        async for chunk in pipeline.llm.astream("Analyze CV quality briefly"):
                            await websocket.send_json({"event": "token", "token": chunk.content})
                            await asyncio.sleep(0.01)

                await websocket.send_json({"event": "node_complete", "node": node_name, "data": {
                    k: v for k, v in state_update.items() if k not in ["cv_data", "cv_embedding"]
                }})

        await websocket.send_json({"event": "complete"})
    except Exception as e:
        logger.error(f"Error: {e}")
        await websocket.send_json({"event": "error", "message": str(e)})
    finally:
        await websocket.close()


# Upload
@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(400, "PDF only")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, "Max 5MB")

    cv_id = str(uuid.uuid4())
    with open(UPLOAD_DIR / f"{cv_id}.pdf", "wb") as f:
        f.write(content)

    return {"cv_id": cv_id}
