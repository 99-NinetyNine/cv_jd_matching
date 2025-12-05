"""
LangGraph-based Batch Status Checker

Refactors the complex check_batch_status_task into a clean state machine.

State Flow:
1. fetch_batches -> Retrieve active batches from DB
2. check_status -> Poll OpenAI API for batch status
3. route_by_status -> Route to appropriate handler based on status
4. handle_completed -> Process completed batches by type
5. handle_failed -> Mark failed items
6. handle_errors -> Process error files
7. update_db -> Commit changes

Benefits:
- Clear separation of concerns
- Easy to test individual nodes
- Visual workflow representation
- Better error handling
- Extensible for new batch types
"""

import logging
from typing import TypedDict, List, Literal, Optional, Dict, Any
from datetime import datetime

from langgraph.graph import StateGraph, END
from sqlmodel import Session, select

from core.db.models import BatchRequest, CV, Job, Prediction
from core.services.batch_service import BatchService

logger = logging.getLogger(__name__)


# Define the state that flows through the graph
class BatchStatusState(TypedDict):
    """State object that flows through the graph nodes."""
    session: Session
    batch_service: BatchService
    batches: List[BatchRequest]
    current_batch: Optional[BatchRequest]
    current_batch_index: int
    remote_batch: Optional[Any]
    results: Optional[List[Dict]]
    stats: Dict[str, int]
    error_message: Optional[str]


# Node Functions
def fetch_batches(state: BatchStatusState) -> BatchStatusState:
    """Fetch active batches from database."""
    logger.info("Fetching active batches...")
    
    active_statuses = ["validating", "in_progress", "finalizing"]
    batches = state["session"].exec(
        select(BatchRequest)
        .where(BatchRequest.status.in_(active_statuses))
        .order_by(BatchRequest.created_at)
        .limit(50)
    ).all()
    
    state["batches"] = list(batches)
    state["current_batch_index"] = 0
    state["stats"] = {"checked": 0, "completed": 0, "failed": 0, "errors_handled": 0}
    
    logger.info(f"Found {len(batches)} active batches")
    return state


def check_next_batch(state: BatchStatusState) -> BatchStatusState:
    """Check if there are more batches to process."""
    batches = state["batches"]
    index = state["current_batch_index"]
    
    if index >= len(batches):
        state["current_batch"] = None
        return state
    
    state["current_batch"] = batches[index]
    state["current_batch_index"] = index + 1
    return state


def poll_batch_status(state: BatchStatusState) -> BatchStatusState:
    """Poll OpenAI API for batch status."""
    batch_req = state["current_batch"]
    batch_service = state["batch_service"]
    
    logger.info(f"Checking status of batch {batch_req.batch_api_id}")
    
    try:
        remote_batch = batch_service.retrieve_batch(batch_req.batch_api_id)
        
        # Update DB record
        batch_req.status = remote_batch.status
        batch_req.request_counts = remote_batch.request_counts
        batch_req.output_file_id = remote_batch.output_file_id
        batch_req.error_file_id = remote_batch.error_file_id
        
        state["remote_batch"] = remote_batch
        state["stats"]["checked"] += 1
        
    except Exception as e:
        logger.error(f"Failed to check batch {batch_req.batch_api_id}: {e}")
        state["error_message"] = str(e)
        state["remote_batch"] = None
    
    return state


def handle_completed_batch(state: BatchStatusState) -> BatchStatusState:
    """Handle completed batches by routing to type-specific handlers."""
    batch_req = state["current_batch"]
    remote_batch = state["remote_batch"]
    batch_service = state["batch_service"]
    session = state["session"]
    
    batch_type = batch_req.batch_metadata.get("type")
    logger.info(f"Processing completed batch {batch_req.batch_api_id} of type {batch_type}")
    
    try:
        # Retrieve results
        results = batch_service.retrieve_results(remote_batch.output_file_id)
        state["results"] = results
        
        # Route to type-specific handler
        if batch_type == "embedding":
            _handle_embedding_results(state)
        elif batch_type == "cv_parsing":
            _handle_cv_parsing_results(state)
        elif batch_type == "explanation_simple":
            _handle_simple_explanation_results(state)
        elif batch_type == "explanation":
            _handle_explanation_results(state)
        else:
            logger.warning(f"Unknown batch type: {batch_type}")
        
        # Update batch record
        batch_req.completed_at = datetime.utcnow()
        batch_req.status = remote_batch.status
        batch_req.output_file_id = remote_batch.output_file_id
        
        state["stats"]["completed"] += 1
        
    except Exception as e:
        logger.error(f"Failed to process completed batch: {e}")
        state["error_message"] = str(e)
    
    return state


def handle_failed_batch(state: BatchStatusState) -> BatchStatusState:
    """Handle failed/expired/cancelled batches."""
    batch_req = state["current_batch"]
    remote_batch = state["remote_batch"]
    batch_service = state["batch_service"]
    session = state["session"]
    
    logger.error(f"Batch {batch_req.batch_api_id} {remote_batch.status}. Marking items as failed.")
    
    batch_req.completed_at = datetime.utcnow()
    batch_req.status = remote_batch.status
    
    batch_type = batch_req.batch_metadata.get("type")
    
    try:
        if batch_req.input_file_id:
            file_content = batch_service.retrieve_results(batch_req.input_file_id)
            
            if batch_type == "embedding":
                _mark_embedding_items_failed(file_content, session)
            elif batch_type == "cv_parsing":
                _mark_cv_parsing_items_failed(file_content, session)
        
        state["stats"]["failed"] += 1
        
    except Exception as e:
        logger.error(f"Failed to mark items as failed: {e}")
        state["error_message"] = str(e)
    
    return state


def handle_error_file(state: BatchStatusState) -> BatchStatusState:
    """Process error file if present."""
    batch_req = state["current_batch"]
    remote_batch = state["remote_batch"]
    batch_service = state["batch_service"]
    session = state["session"]
    
    if not remote_batch.error_file_id:
        return state
    
    logger.warning(f"Processing error file for batch {batch_req.batch_api_id}")
    
    try:
        errors = batch_service.retrieve_results(remote_batch.error_file_id)
        batch_type = batch_req.batch_metadata.get("type")
        
        for error_entry in errors:
            custom_id = error_entry.get("custom_id")
            if not custom_id:
                continue
            
            error_msg = error_entry.get("error", {}).get("message", "Unknown error")
            logger.warning(f"Batch error for {custom_id}: {error_msg}")
            
            # Mark item as failed based on type
            if batch_type == "embedding":
                _mark_single_embedding_failed(custom_id, session)
            elif batch_type == "cv_parsing":
                _mark_single_cv_parsing_failed(custom_id, session)
        
        state["stats"]["errors_handled"] += len(errors)
        logger.info(f"Processed {len(errors)} errors from batch {batch_req.batch_api_id}")
        
    except Exception as e:
        logger.error(f"Failed to process error file: {e}")
        state["error_message"] = str(e)
    
    return state


def commit_changes(state: BatchStatusState) -> BatchStatusState:
    """Commit all changes to database."""
    batch_req = state["current_batch"]
    session = state["session"]
    
    try:
        session.add(batch_req)
        session.commit()
        logger.info(f"Committed changes for batch {batch_req.batch_api_id}")
    except Exception as e:
        logger.error(f"Failed to commit changes: {e}")
        session.rollback()
        state["error_message"] = str(e)
    
    return state


# Routing Functions
def should_continue(state: BatchStatusState) -> Literal["check_next", "end"]:
    """Determine if there are more batches to process."""
    if state["current_batch"] is None:
        return "end"
    return "check_next"


def route_by_status(state: BatchStatusState) -> Literal["completed", "failed", "next_batch"]:
    """Route based on batch status."""
    remote_batch = state["remote_batch"]
    
    if not remote_batch:
        return "next_batch"
    
    if remote_batch.status == "completed":
        return "completed"
    elif remote_batch.status in ["failed", "expired", "cancelled"]:
        return "failed"
    else:
        return "next_batch"


def should_check_errors(state: BatchStatusState) -> Literal["check_errors", "commit"]:
    """Determine if error file needs processing."""
    remote_batch = state["remote_batch"]
    
    if remote_batch and remote_batch.error_file_id:
        return "check_errors"
    return "commit"


# Type-specific handlers (extracted from original code)
def _handle_embedding_results(state: BatchStatusState):
    """Handle embedding batch results."""
    results = state["results"]
    session = state["session"]
    
    for res in results:
        custom_id = res.get("custom_id")
        if not custom_id:
            continue
        
        if custom_id.startswith("cv-"):
            cv_id = int(custom_id.replace("cv-", ""))
            cv = session.get(CV, cv_id)
            if cv:
                try:
                    embedding = res["response"]["body"]["data"][0]["embedding"]
                    cv.embedding = embedding
                    cv.embedding_status = "completed"
                    session.add(cv)
                except Exception as e:
                    logger.error(f"Failed to update CV {cv_id}: {e}")
                    cv.embedding_status = "failed"
                    session.add(cv)
        
        elif custom_id.startswith("job-"):
            job_id = int(custom_id.replace("job-", ""))
            job = session.get(Job, job_id)
            if job:
                try:
                    embedding = res["response"]["body"]["data"][0]["embedding"]
                    job.embedding = embedding
                    job.embedding_status = "completed"
                    session.add(job)
                except Exception as e:
                    logger.error(f"Failed to update Job {job_id}: {e}")
                    job.embedding_status = "failed"
                    session.add(job)


def _handle_cv_parsing_results(state: BatchStatusState):
    """Handle CV parsing batch results."""
    from core.parsing.batch_parser import BatchCVParser
    
    batch_req = state["current_batch"]
    session = state["session"]
    
    batch_parser = BatchCVParser()
    stats = batch_parser.process_parsing_results(batch_req, session)
    logger.info(f"CV parsing stats: {stats}")


def _handle_simple_explanation_results(state: BatchStatusState):
    """Handle simple explanation batch results."""
    from core.matching.batch_explainer import SimpleBatchExplainer
    
    batch_req = state["current_batch"]
    session = state["session"]
    
    explainer = SimpleBatchExplainer()
    stats = explainer.process_explanation_results(batch_req, session)
    logger.info(f"Simple explanation stats: {stats}")


def _handle_explanation_results(state: BatchStatusState):
    """Handle explanation batch results."""
    results = state["results"]
    session = state["session"]
    
    # Group by prediction_id
    updates = {}  # prediction_id -> {job_id: explanation}
    
    for res in results:
        custom_id = res.get("custom_id")
        if not custom_id:
            continue
        
        try:
            # custom_id format: pred-{prediction_id}-job-{job_id}
            parts = custom_id.split("-job-")
            if len(parts) != 2:
                continue
            
            pred_part = parts[0].replace("pred-", "")
            job_id = parts[1]
            
            explanation = res["response"]["body"]["choices"][0]["message"]["content"]
            
            if pred_part not in updates:
                updates[pred_part] = {}
            updates[pred_part][job_id] = explanation
        except Exception as e:
            logger.error(f"Failed to parse explanation result {custom_id}: {e}")
    
    # Update Predictions
    for pred_id, job_explanations in updates.items():
        prediction = session.exec(
            select(Prediction).where(Prediction.prediction_id == pred_id)
        ).first()
        if prediction:
            new_matches = []
            for m in prediction.matches:
                if m["job_id"] in job_explanations:
                    m["explanation"] = job_explanations[m["job_id"]]
                new_matches.append(m)
            
            prediction.matches = list(new_matches)
            session.add(prediction)


def _mark_embedding_items_failed(file_content: List[Dict], session: Session):
    """Mark embedding items as failed."""
    for line in file_content:
        custom_id = line.get("custom_id")
        if not custom_id:
            continue
        
        if custom_id.startswith("cv-"):
            cv_id = int(custom_id.replace("cv-", ""))
            cv = session.get(CV, cv_id)
            if cv:
                cv.embedding_status = "failed"
                session.add(cv)
        
        elif custom_id.startswith("job-"):
            job_id = int(custom_id.replace("job-", ""))
            job = session.get(Job, job_id)
            if job:
                job.embedding_status = "failed"
                session.add(job)


def _mark_cv_parsing_items_failed(file_content: List[Dict], session: Session):
    """Mark CV parsing items as failed."""
    for line in file_content:
        custom_id = line.get("custom_id")
        if custom_id and custom_id.startswith("cv-parse-"):
            cv_id = int(custom_id.replace("cv-parse-", ""))
            cv = session.get(CV, cv_id)
            if cv:
                cv.parsing_status = "failed"
                session.add(cv)


def _mark_single_embedding_failed(custom_id: str, session: Session):
    """Mark a single embedding item as failed."""
    if custom_id.startswith("cv-"):
        cv_id = int(custom_id.replace("cv-", ""))
        cv = session.get(CV, cv_id)
        if cv:
            cv.embedding_status = "failed"
            session.add(cv)
    
    elif custom_id.startswith("job-"):
        job_id = int(custom_id.replace("job-", ""))
        job = session.get(Job, job_id)
        if job:
            job.embedding_status = "failed"
            session.add(job)


def _mark_single_cv_parsing_failed(custom_id: str, session: Session):
    """Mark a single CV parsing item as failed."""
    if custom_id.startswith("cv-parse-"):
        cv_id = int(custom_id.replace("cv-parse-", ""))
        cv = session.get(CV, cv_id)
        if cv:
            cv.parsing_status = "failed"
            session.add(cv)


# Build the graph
def create_batch_status_graph() -> StateGraph:
    """Create the LangGraph workflow for batch status checking."""
    
    workflow = StateGraph(BatchStatusState)
    
    # Add nodes
    workflow.add_node("fetch_batches", fetch_batches)
    workflow.add_node("check_next", check_next_batch)
    workflow.add_node("poll_status", poll_batch_status)
    workflow.add_node("handle_completed", handle_completed_batch)
    workflow.add_node("handle_failed", handle_failed_batch)
    workflow.add_node("handle_errors", handle_error_file)
    workflow.add_node("commit", commit_changes)
    
    # Define edges
    workflow.set_entry_point("fetch_batches")
    workflow.add_edge("fetch_batches", "check_next")
    
    # Check if more batches exist
    workflow.add_conditional_edges(
        "check_next",
        should_continue,
        {
            "check_next": "poll_status",
            "end": END
        }
    )
    
    # Route based on batch status
    workflow.add_conditional_edges(
        "poll_status",
        route_by_status,
        {
            "completed": "handle_completed",
            "failed": "handle_failed",
            "next_batch": "check_next"
        }
    )
    
    # After handling completed, check for errors
    workflow.add_conditional_edges(
        "handle_completed",
        should_check_errors,
        {
            "check_errors": "handle_errors",
            "commit": "commit"
        }
    )
    
    # After handling failed, commit
    workflow.add_edge("handle_failed", "commit")
    
    # After handling errors, commit
    workflow.add_edge("handle_errors", "commit")
    
    # After commit, check next batch
    workflow.add_edge("commit", "check_next")
    
    return workflow.compile()


# Main execution function
def run_batch_status_check(session: Session, batch_service: BatchService) -> Dict[str, Any]:
    """
    Execute the batch status check workflow.
    
    Args:
        session: Database session
        batch_service: Batch service instance
    
    Returns:
        Statistics about processed batches
    """
    # Create the graph
    graph = create_batch_status_graph()
    
    # Initialize state
    initial_state: BatchStatusState = {
        "session": session,
        "batch_service": batch_service,
        "batches": [],
        "current_batch": None,
        "current_batch_index": 0,
        "remote_batch": None,
        "results": None,
        "stats": {},
        "error_message": None
    }
    
    # Run the graph
    final_state = graph.invoke(initial_state)
    
    # Return statistics
    return {
        "status": "success" if not final_state.get("error_message") else "error",
        "stats": final_state["stats"],
        "error": final_state.get("error_message")
    }


def visualize_graph(output_path: str = "batch_status_graph.png") -> str:
    """
    Visualize the LangGraph workflow and save as PNG using Mermaid.ink API.
    
    This uses LangGraph's built-in visualization capabilities to generate
    a professional diagram of the state machine.
    
    Args:
        output_path: Path to save the PNG image (default: batch_status_graph.png)
    
    Returns:
        Path to the saved image or Mermaid diagram string
    
    Usage:
        # Generate and save PNG
        visualize_graph("workflow.png")
        
        # Or just get the Mermaid diagram
        mermaid_code = get_mermaid_diagram()
        print(mermaid_code)
    """
    try:
        from IPython.display import Image, display
        import requests
        import base64
        import urllib.parse
        
        # Create the graph
        graph = create_batch_status_graph()
        
        # Get Mermaid diagram from LangGraph
        mermaid_diagram = graph.get_graph().draw_mermaid()
        
        # Encode for Mermaid.ink API
        graphbytes = mermaid_diagram.encode("utf8")
        base64_bytes = base64.b64encode(graphbytes)
        base64_string = base64_bytes.decode("ascii")
        
        # Generate image URL
        mermaid_url = f"https://mermaid.ink/img/{base64_string}"
        
        # Download and save the image
        response = requests.get(mermaid_url)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            logger.info(f"Graph visualization saved to {output_path}")
            return output_path
        else:
            logger.warning(f"Failed to download image: {response.status_code}")
            return mermaid_diagram
            
    except ImportError:
        logger.warning("IPython or requests not available. Returning Mermaid diagram only.")
        graph = create_batch_status_graph()
        return graph.get_graph().draw_mermaid()
    except Exception as e:
        logger.error(f"Failed to visualize graph: {e}")
        return f"Error: {e}"


 
   
