"""
Advanced Candidate Explainability Router

Demonstrates LangGraph streaming with multiple explainability approaches:
- CV Quality Scoring (ATS Resume Quality Assessment)
- Contrastive Explanations (Why CV A vs CV B)
- Counterfactual Suggestions (What changes would improve match)
- Chain-of-Thought Match Reasoning
- Interactive streaming via WebSocket

Showcases: ReAct patterns, CoT reasoning, streaming graph nodes
"""

from fastapi import APIRouter, WebSocket, Depends, HTTPException
from sqlmodel import Session, select
from typing import Dict, Any, List, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from pathlib import Path
import json
import logging

from core.db.engine import get_session
from core.db.models import CV, Job, Prediction
from core.llm.factory import get_llm
from core.configs import USE_REAL_LLM

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/advanced", tags=["advanced-candidate"])

UPLOAD_DIR = Path("uploads")


# ============================================================================
# LangGraph State Definition
# ============================================================================

class ExplainabilityState(TypedDict):
    """State for the explainability workflow."""
    cv_id: str
    cv_data: Dict[str, Any]
    cv_text: str
    top_matches: List[Dict[str, Any]]

    # Node outputs
    quality_score: Dict[str, Any]
    contrastive_explanation: str
    counterfactual_suggestions: List[str]
    cot_reasoning: str

    # Metadata
    current_node: str
    error: str


# ============================================================================
# LangGraph Nodes (Explainability Functions)
# ============================================================================

class CVExplainabilityGraph:
    """LangGraph workflow for advanced CV explainability."""

    def __init__(self):
        self.llm = get_llm()
        self.app = self._build_graph()

    def _build_graph(self):
        """Build the explainability workflow graph."""
        workflow = StateGraph(ExplainabilityState)

        # Add nodes
        workflow.add_node("assess_quality", self.assess_cv_quality)
        workflow.add_node("contrastive_explain", self.generate_contrastive_explanation)
        workflow.add_node("counterfactual_suggest", self.generate_counterfactual_suggestions)
        workflow.add_node("cot_reasoning", self.chain_of_thought_reasoning)

        # Define edges
        workflow.set_entry_point("assess_quality")
        workflow.add_edge("assess_quality", "contrastive_explain")
        workflow.add_edge("contrastive_explain", "counterfactual_suggest")
        workflow.add_edge("counterfactual_suggest", "cot_reasoning")
        workflow.add_edge("cot_reasoning", END)

        # Add memory for checkpointing (optional but shows advanced feature)
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)

    # ------------------------------------------------------------------------
    # Node 1: CV Quality Scoring (ATS Resume Assessment)
    # ------------------------------------------------------------------------

    def assess_cv_quality(self, state: ExplainabilityState) -> Dict[str, Any]:
        """
        Assess CV quality using LLM-based scoring.

        Evaluates:
        - Structure & Formatting
        - Content Completeness
        - ATS Compatibility
        - Keyword Optimization
        - Professional Language
        """
        cv_data = state["cv_data"]
        cv_text = state["cv_text"]

        prompt = f"""You are an expert ATS (Applicant Tracking System) and resume quality assessor.

Analyze this CV and provide structured scoring:

CV DATA:
{json.dumps(cv_data, indent=2)[:1500]}

TASK:
1. Score each category (0-100):
   - structure_formatting: Layout, sections, readability
   - content_completeness: All key sections present (skills, experience, education)
   - ats_compatibility: Machine-readable, keyword-rich
   - keyword_optimization: Relevant skills and tech terms
   - professional_language: Clear, concise, error-free

2. Provide overall_score (weighted average)

3. List top 3 improvement_suggestions

Return JSON format:
{{
  "structure_formatting": <score>,
  "content_completeness": <score>,
  "ats_compatibility": <score>,
  "keyword_optimization": <score>,
  "professional_language": <score>,
  "overall_score": <score>,
  "improvement_suggestions": ["suggestion1", "suggestion2", "suggestion3"]
}}
"""

        if USE_REAL_LLM is False:
            quality_score = {
                "structure_formatting": 85,
                "content_completeness": 78,
                "ats_compatibility": 82,
                "keyword_optimization": 75,
                "professional_language": 88,
                "overall_score": 82,
                "improvement_suggestions": [
                    "Add quantifiable achievements with metrics",
                    "Include more technical keywords relevant to target roles",
                    "Expand project descriptions with technologies used"
                ]
            }
        else:
            response = self.llm.invoke(prompt)
            # Parse JSON from LLM response
            try:
                quality_score = json.loads(response.content)
            except:
                quality_score = {"overall_score": 75, "improvement_suggestions": ["Unable to parse detailed assessment"]}

        return {
            "quality_score": quality_score,
            "current_node": "assess_quality"
        }

    # ------------------------------------------------------------------------
    # Node 2: Contrastive Explanation
    # ------------------------------------------------------------------------

    def generate_contrastive_explanation(self, state: ExplainabilityState) -> Dict[str, Any]:
        """
        Generate contrastive explanation: Why was Job A ranked higher than Job B?

        Compares top 2 matches to explain ranking differences.
        """
        top_matches = state["top_matches"]
        cv_text = state["cv_text"]

        if len(top_matches) < 2:
            return {
                "contrastive_explanation": "Only one match available, no comparison possible.",
                "current_node": "contrastive_explain"
            }

        job_a = top_matches[0]
        job_b = top_matches[1]

        prompt = f"""You are an AI career advisor explaining job match rankings.

CANDIDATE PROFILE:
{cv_text[:800]}

JOB A (Ranked #1):
Title: {job_a.get('title', 'N/A')}
Company: {job_a.get('company', 'N/A')}
Match Score: {job_a.get('match_score', 'N/A')}

JOB B (Ranked #2):
Title: {job_b.get('title', 'N/A')}
Company: {job_b.get('company', 'N/A')}
Match Score: {job_b.get('match_score', 'N/A')}

TASK:
Explain in 3-4 sentences WHY Job A was ranked higher than Job B for this candidate.
Focus on:
- Skills alignment differences
- Experience relevance
- Role fit
- Career progression logic

Be specific and reference candidate's actual background.
"""

        if USE_REAL_LLM is False:
            explanation = f"Job A ('{job_a.get('title')}') ranks higher because it better aligns with the candidate's technical stack and experience level. While Job B is also relevant, Job A offers stronger skills match and clearer career progression based on the candidate's background."
        else:
            response = self.llm.invoke(prompt)
            explanation = response.content

        return {
            "contrastive_explanation": explanation,
            "current_node": "contrastive_explain"
        }

    # ------------------------------------------------------------------------
    # Node 3: Counterfactual Suggestions
    # ------------------------------------------------------------------------

    def generate_counterfactual_suggestions(self, state: ExplainabilityState) -> Dict[str, Any]:
        """
        Generate counterfactual suggestions: What minimal changes would improve match scores?

        Example: "Adding React.js proficiency would increase score from 72 to 85 for Job X"
        """
        cv_data = state["cv_data"]
        top_matches = state["top_matches"]

        if not top_matches:
            return {
                "counterfactual_suggestions": [],
                "current_node": "counterfactual_suggest"
            }

        top_job = top_matches[0]

        prompt = f"""You are a career coach providing actionable CV improvement advice.

CANDIDATE CV:
{json.dumps(cv_data, indent=2)[:1000]}

TOP MATCHED JOB:
Title: {top_job.get('title', 'N/A')}
Missing Skills: {top_job.get('missing_skills', [])}
Current Match Score: {top_job.get('match_score', 'N/A')}

TASK:
Provide 3 COUNTERFACTUAL suggestions in format:
"If you [specific change], your match score would improve from X to Y for roles like [job title]"

Examples:
- "If you add 6+ months experience with Docker/Kubernetes, your match score would improve from 72 to 85 for DevOps Engineer roles"
- "If you include a Python data analysis project with pandas/numpy, your match score would improve from 68 to 80 for Data Analyst positions"

Be specific, realistic, and quantitative.

Return JSON list:
["suggestion1", "suggestion2", "suggestion3"]
"""

        if USE_REAL_LLM is False:
            suggestions = [
                f"If you add cloud platform certifications (AWS/Azure), your match score would improve from {top_job.get('match_score', 70):.0f} to 85+ for cloud-focused roles",
                "If you include 2-3 GitHub projects showcasing missing skills, your match score would improve by 8-12 points",
                "If you quantify achievements with metrics (e.g., 'Improved performance by 40%'), your match score would improve by 5-10 points"
            ]
        else:
            response = self.llm.invoke(prompt)
            try:
                suggestions = json.loads(response.content)
            except:
                suggestions = [response.content]

        return {
            "counterfactual_suggestions": suggestions,
            "current_node": "counterfactual_suggest"
        }

    # ------------------------------------------------------------------------
    # Node 4: Chain-of-Thought Reasoning
    # ------------------------------------------------------------------------

    def chain_of_thought_reasoning(self, state: ExplainabilityState) -> Dict[str, Any]:
        """
        Generate detailed Chain-of-Thought reasoning for the top match.

        Shows step-by-step reasoning process:
        1. Initial skill scan
        2. Experience level assessment
        3. Cultural/role fit analysis
        4. Final decision synthesis
        """
        cv_text = state["cv_text"]
        top_matches = state["top_matches"]

        if not top_matches:
            return {
                "cot_reasoning": "No matches available for reasoning.",
                "current_node": "cot_reasoning"
            }

        top_job = top_matches[0]

        prompt = f"""You are an AI recruiter explaining your matching decision process step-by-step.

CANDIDATE:
{cv_text[:900]}

JOB:
Title: {top_job.get('title', 'N/A')}
Company: {top_job.get('company', 'N/A')}
Required Skills: {top_job.get('missing_skills', [])[:5]}

TASK:
Provide CHAIN-OF-THOUGHT reasoning in exactly 4 steps:

Step 1 - Initial Skill Scan:
[What technical skills did you identify? Which match the job?]

Step 2 - Experience Level Assessment:
[Years of experience? Seniority match? Domain expertise?]

Step 3 - Role Fit Analysis:
[Does the role align with career trajectory? Growth potential?]

Step 4 - Final Decision:
[Synthesize above into overall match quality and confidence level]

Use clear numbered format. Be specific with examples from the CV.
"""

        if USE_REAL_LLM is False:
            reasoning = f"""Step 1 - Initial Skill Scan:
Identified strong technical foundation in core technologies. Matches {len(top_job.get('matched_skills', []))} out of {len(top_job.get('matched_skills', [])) + len(top_job.get('missing_skills', []))} required skills for {top_job.get('title')}.

Step 2 - Experience Level Assessment:
Experience level aligns with job requirements. Demonstrated progression in relevant domain.

Step 3 - Role Fit Analysis:
Role represents logical next step in career trajectory. Company size and culture appear compatible.

Step 4 - Final Decision:
Strong match (score: {top_job.get('match_score', 75):.0f}/100) with high confidence. Primary gaps are learnable skills that don't significantly impact core competency fit."""
        else:
            response = self.llm.invoke(prompt)
            reasoning = response.content

        return {
            "cot_reasoning": reasoning,
            "current_node": "cot_reasoning"
        }


# ============================================================================
# WebSocket Endpoint with Streaming
# ============================================================================

@router.websocket("/ws/explain/{cv_id}")
async def advanced_explainability_websocket(
    websocket: WebSocket,
    cv_id: str,
    session: Session = Depends(get_session)
):
    """
    Advanced CV explainability via WebSocket with streaming graph nodes.

    Stream events:
    - node_start: When a node begins processing
    - node_complete: When a node finishes (includes results)
    - complete: Final aggregated results
    - error: If any error occurs

    Example client:
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/advanced/ws/explain/{cv_id}');
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log(data.event, data.node, data.data);
    };
    ```
    """
    await websocket.accept()

    try:
        # 1. Fetch CV data
        await websocket.send_json({
            "event": "init",
            "message": "Fetching CV data..."
        })

        cv = session.exec(select(CV).where(CV.id == int(cv_id))).first()
        if not cv or not cv.content:
            await websocket.send_json({
                "event": "error",
                "message": "CV not found or not parsed"
            })
            await websocket.close()
            return

        # 2. Get top predictions/matches
        latest_prediction = session.exec(
            select(Prediction)
            .where(Prediction.cv_id == cv_id)
            .order_by(Prediction.created_at.desc())
        ).first()

        if not latest_prediction or not latest_prediction.matches:
            await websocket.send_json({
                "event": "error",
                "message": "No matches found. Please run matching first."
            })
            await websocket.close()
            return

        top_matches = latest_prediction.matches[:2]  # Top 2 for comparison

        # 3. Prepare CV text representation
        basics = cv.content.get("basics", {})
        skills = cv.content.get("skills", [])
        work = cv.content.get("work", [])

        cv_text = f"""
Name: {basics.get('name', 'Unknown')}
Email: {basics.get('email', 'N/A')}
Skills: {', '.join([s.get('name', '') for s in skills[:10]])}
Experience: {len(work)} positions
"""

        # 4. Initialize graph
        graph = CVExplainabilityGraph()

        # 5. Prepare initial state
        initial_state = {
            "cv_id": cv_id,
            "cv_data": cv.content,
            "cv_text": cv_text,
            "top_matches": top_matches,
            "quality_score": {},
            "contrastive_explanation": "",
            "counterfactual_suggestions": [],
            "cot_reasoning": "",
            "current_node": "",
            "error": ""
        }

        # 6. Stream graph execution
        config = {"configurable": {"thread_id": cv_id}}

        final_state = None

        # Stream events from graph
        async for event in graph.app.astream(initial_state, config):
            # event is dict with node_name: state_update
            for node_name, state_update in event.items():
                # Send node start event
                await websocket.send_json({
                    "event": "node_start",
                    "node": node_name,
                    "message": f"Processing {node_name.replace('_', ' ')}..."
                })

                # Send node complete event with results
                await websocket.send_json({
                    "event": "node_complete",
                    "node": node_name,
                    "data": {
                        k: v for k, v in state_update.items()
                        if k not in ["cv_data", "cv_text", "top_matches"]  # Exclude large data
                    }
                })

                final_state = state_update

        # 7. Send final complete event
        await websocket.send_json({
            "event": "complete",
            "data": {
                "quality_score": final_state.get("quality_score", {}),
                "contrastive_explanation": final_state.get("contrastive_explanation", ""),
                "counterfactual_suggestions": final_state.get("counterfactual_suggestions", []),
                "cot_reasoning": final_state.get("cot_reasoning", "")
            }
        })

    except Exception as e:
        logger.error(f"Advanced explainability error: {e}", exc_info=True)
        await websocket.send_json({
            "event": "error",
            "message": str(e)
        })
    finally:
        await websocket.close()


# ============================================================================
# REST Endpoint (Non-streaming alternative)
# ============================================================================

@router.get("/explain/{cv_id}")
async def advanced_explainability_rest(
    cv_id: str,
    session: Session = Depends(get_session)
):
    """
    REST version of advanced explainability (non-streaming).

    Returns all results in a single response.
    Use WebSocket endpoint for streaming experience.
    """
    # Fetch CV
    cv = session.exec(select(CV).where(CV.id == int(cv_id))).first()
    if not cv or not cv.content:
        raise HTTPException(status_code=404, detail="CV not found or not parsed")

    # Get predictions
    latest_prediction = session.exec(
        select(Prediction)
        .where(Prediction.cv_id == cv_id)
        .order_by(Prediction.created_at.desc())
    ).first()

    if not latest_prediction or not latest_prediction.matches:
        raise HTTPException(status_code=404, detail="No matches found. Run matching first.")

    top_matches = latest_prediction.matches[:2]

    # CV text
    basics = cv.content.get("basics", {})
    skills = cv.content.get("skills", [])
    work = cv.content.get("work", [])

    cv_text = f"""
Name: {basics.get('name', 'Unknown')}
Skills: {', '.join([s.get('name', '') for s in skills[:10]])}
Experience: {len(work)} positions
"""

    # Run graph
    graph = CVExplainabilityGraph()
    initial_state = {
        "cv_id": cv_id,
        "cv_data": cv.content,
        "cv_text": cv_text,
        "top_matches": top_matches,
        "quality_score": {},
        "contrastive_explanation": "",
        "counterfactual_suggestions": [],
        "cot_reasoning": "",
        "current_node": "",
        "error": ""
    }

    config = {"configurable": {"thread_id": cv_id}}
    final_state = graph.app.invoke(initial_state, config)

    return {
        "cv_id": cv_id,
        "quality_score": final_state.get("quality_score", {}),
        "contrastive_explanation": final_state.get("contrastive_explanation", ""),
        "counterfactual_suggestions": final_state.get("counterfactual_suggestions", []),
        "cot_reasoning": final_state.get("cot_reasoning", ""),
        "analyzed_matches": len(top_matches)
    }
