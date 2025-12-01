from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pathlib import Path
import uuid
import shutil
from sqlmodel import Session, select
from core.db.engine import get_session
from core.db.models import BatchJob
from core.worker.tasks import process_batch_upload
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["batch"])

UPLOAD_DIR = Path("uploads/batch")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/batch/cvs")
async def batch_upload_cvs(file: UploadFile = File(...), session: Session = Depends(get_session)):
    """
    Upload a ZIP file containing multiple CVs (PDFs) for batch processing.
    """
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files are allowed")
        
    batch_id = str(uuid.uuid4())
    filename = f"{batch_id}.zip"
    file_path = UPLOAD_DIR / filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Create BatchJob record
        batch_job = BatchJob(
            batch_id=batch_id,
            status="pending",
            type="cv_bulk_upload"
        )
        session.add(batch_job)
        session.commit()
        
        # Trigger Celery task
        process_batch_upload.delay(batch_id, str(file_path))
        
        return {
            "batch_id": batch_id,
            "status": "pending",
            "message": "Batch upload accepted. Processing started."
        }
        
    except Exception as e:
        logger.error(f"Batch upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/batch/{batch_id}")
async def get_batch_status(batch_id: str, session: Session = Depends(get_session)):
    """
    Get the status and results of a batch job.
    """
    batch_job = session.exec(select(BatchJob).where(BatchJob.batch_id == batch_id)).first()
    
    if not batch_job:
        raise HTTPException(status_code=404, detail="Batch job not found")
        
    return batch_job
