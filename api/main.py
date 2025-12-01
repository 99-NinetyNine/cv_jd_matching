from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from core.pipeline import ResumeExtractionPipeline
from api.routers import auth, candidate, hirer
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
app.include_router(auth.router)
app.include_router(candidate.router)
app.include_router(hirer.router)

# Initialize Pipeline (Common Class)
# This class encapsulates all logic (Layout Parsing, Extraction, Evaluation)
pipeline = ResumeExtractionPipeline()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/health")
def health_check():
    return {"status": "healthy"}
