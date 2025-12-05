from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from api.routers import auth, candidate, hirer, admin, interactions, super_advanced
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
app.include_router(candidate.router)  # Legacy matching (keep for backward compat)
app.include_router(hirer.router)
app.include_router(interactions.router)
app.include_router(admin.router)
app.include_router(super_advanced.router)  # 🔥 THE ULTIMATE UNIFIED SYSTEM!

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

@app.get("/health")
def health_check():
    return {"status": "healthy"}
