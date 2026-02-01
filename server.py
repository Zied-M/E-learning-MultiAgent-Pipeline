from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import os
from src.orchestrator import Orchestrator

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
app.mount("/static", StaticFiles(directory="web"), name="static")
@app.get("/")
def read_root():
    from fastapi.responses import FileResponse
    return FileResponse('web/index.html')

# Configuration for Orchestrator
CONFIG = {
    "profiles_path": "data/demo/learner_profiles.json",
    "logs_dir": "data/demo/logs",
    "topic_graph_path": "data/demo/topic_graph.yaml",
    "resources_path": "data/demo/resources.jsonl",
    "qa_rules_path": "config/qa_rules.yaml",
    "oulad_dir": "data/raw/OULAD",
    "model": "llama3"
}

class LearnerProfile(BaseModel):
    learner_id: str
    name: str
    level: str
    strengths: List[str]
    weaknesses: List[str]
    pace: str
    engagement: str
    preferences: Dict[str, Any]

class PipelineRequest(BaseModel):
    learner_id: str
    goal: str

@app.get("/profiles")
async def get_profiles():
    if not os.path.exists(CONFIG["profiles_path"]):
        return {}
    with open(CONFIG["profiles_path"], "r") as f:
        return json.load(f)

@app.post("/profiles")
async def save_profile(profile: LearnerProfile):
    profiles = {}
    if os.path.exists(CONFIG["profiles_path"]):
        with open(CONFIG["profiles_path"], "r") as f:
            profiles = json.load(f)
    
    profiles[profile.learner_id] = profile.dict()
    
    with open(CONFIG["profiles_path"], "w") as f:
        json.dump(profiles, f, indent=4)
    
    return {"status": "success"}

@app.post("/run")
async def run_pipeline(request: PipelineRequest):
    try:
        orchestrator = Orchestrator(CONFIG)
        result = orchestrator.run(request.learner_id, request.goal)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trace")
async def get_trace():
    if not os.path.exists("trace.log"):
        return {"trace": ""}
    with open("trace.log", "r") as f:
        return {"trace": f.read()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
