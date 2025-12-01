from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from core.pipeline import ResumeExtractionPipeline
from api.routers import candidate, hirer, batch
import shutil
import os
import uuid

app = FastAPI(title="CV Matching Platform API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(candidate.router)
app.include_router(hirer.router)
app.include_router(batch.router)

# Initialize Pipeline (Common Class)
# This class encapsulates all logic (Layout Parsing, Extraction, Evaluation)
pipeline = ResumeExtractionPipeline()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/extract")
async def extract_resume(file: UploadFile = File(...)):
    """
    Upload a PDF resume and get structured JSON data.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    # Save file
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Run Pipeline
        result = pipeline.process(file_path)
        
        # Cleanup (optional)
        # os.remove(file_path)
        
        return result
        
    except Exception as e:
        # Log error
        print(f"Error processing file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy"}
