from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import json
import asyncio

from core.graph.parsing_graph import create_parsing_graph
from core.graph.matching_graph import create_matching_graph
from core.db.engine import create_db_and_tables
from api.routers import hirer, candidate

app = FastAPI(title="CV-Job Matching System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="api/static"), name="static")

# Include Routers
app.include_router(hirer.router)
app.include_router(candidate.router)

# Startup event handler
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.get("/")
async def root():
    return {"message": "Welcome to CV-Job Matching System API"}

@app.websocket("/ws/process/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "parse_cv":
                filename = message["filename"]
                file_path = str(UPLOAD_DIR / filename)
                
                graph = create_parsing_graph()
                
                await websocket.send_json({"status": "Starting parsing workflow..."})
                
                inputs = {"file_path": file_path}
                async for event in graph.astream(inputs):
                    for key, value in event.items():
                        if "status" in value:
                            await websocket.send_json({"status": value["status"]})
                        if "structured_data" in value:
                            PROCESSED_CVS[client_id] = value["structured_data"]
                            await websocket.send_json({
                                "status": "Parsing complete", 
                                "data": value["structured_data"]
                            })
                            
            elif message["type"] == "match_jobs":
                if client_id not in PROCESSED_CVS:
                    await websocket.send_json({"error": "No CV parsed for this client yet."})
                    continue
                    
                cv_data = PROCESSED_CVS[client_id]
                graph = create_matching_graph()
                
                await websocket.send_json({"status": "Starting matching workflow..."})
                
                inputs = {
                    "cv_data": cv_data,
                    "job_descriptions": JOB_DESCRIPTIONS
                }
                
                async for event in graph.astream(inputs):
                    for key, value in event.items():
                        if "status" in value:
                            await websocket.send_json({"status": value["status"]})
                        if "matches" in value:
                            await websocket.send_json({
                                "status": "Matching complete", 
                                "matches": value["matches"]
                            })

    except WebSocketDisconnect:
        print(f"Client #{client_id} disconnected")
