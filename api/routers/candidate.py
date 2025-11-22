from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pathlib import Path
import uuid
from sqlmodel import Session, select
from core.db.engine import get_session
from core.db.models import Job, CV
from core.matching.semantic_matcher import HybridMatcher
from core.parsing.pdf_parser import PDFParser

router = APIRouter(tags=["candidate"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@router.post("/upload")
async def upload_cv(file: UploadFile = File(...), session: Session = Depends(get_session)):
    # Validation
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
        
    content = await file.read()
    if len(content) > 5 * 1024 * 1024: # 5MB
        raise HTTPException(status_code=400, detail="File is too large. Maximum size is 5MB.")
    
    file.file.seek(0)

    cv_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix
    if not file_extension:
        file_extension = ".pdf"
        
    filename = f"{cv_id}{file_extension}"
    file_path = UPLOAD_DIR / filename
    
    with open(file_path, "wb") as buffer:
        buffer.write(content)
        
    # Create initial CV record
    cv = CV(filename=filename, content={})
    session.add(cv)
    session.commit()
    session.refresh(cv)
    
    return {"cv_id": cv_id, "filename": filename, "path": str(file_path)}

@router.post("/candidates/match")
async def match_candidate(cv_data: dict, session: Session = Depends(get_session)):
    # Match a candidate against all jobs
    # Get all jobs from DB
    jobs = session.exec(select(Job)).all()
    job_dicts = [job.dict() for job in jobs]
    
    matcher = HybridMatcher()
    matches = matcher.match(cv_data, job_dicts)
    return {"matches": matches}

@router.post("/parse_sync")
async def parse_cv_sync(cv_id: str, session: Session = Depends(get_session)):
    # Find the file
    filename = f"{cv_id}.pdf"
    file_path = UPLOAD_DIR / filename
    
    if not file_path.exists():
         raise HTTPException(status_code=404, detail="CV file not found.")

    parser = PDFParser()
    try:
        data = parser.parse(file_path)
        
        # Update CV record with parsed content
        # We need to find the CV by filename (which contains the ID)
        cv = session.exec(select(CV).where(CV.filename == filename)).first()
        if cv:
            cv.content = data
            # In a real app, we'd generate embedding here
            session.add(cv)
            session.commit()
            
        return data
    except Exception as e:
        print(f"Parsing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")
