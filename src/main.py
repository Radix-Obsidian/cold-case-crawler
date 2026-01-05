from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import os
import asyncio
import json
from typing import Optional, List

# Import our services
from src.models.case import CaseFile, Evidence
from src.services.debate import create_debate_engine
from src.services.audio import create_audio_service

# Import API routers
from src.api.membership import router as membership_router

# Import case selector for database access
try:
    from src.services.case_selector import create_case_selector
    CASE_SELECTOR_AVAILABLE = True
except ImportError:
    CASE_SELECTOR_AVAILABLE = False

app = FastAPI(title="Dead Air API")

# Include membership routes
app.include_router(membership_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class CaseRequest(BaseModel):
    title: str
    description: str
    location: str = "Unknown Location"
    date: str = "Unknown Date"

class GenerationResponse(BaseModel):
    status: str
    message: str
    audio_url: Optional[str] = None

# Global state for simple demo (in production use a DB)
current_task = None

async def generate_episode_task(case_req: CaseRequest):
    """
    Background task to generate the episode.
    In a real app, this would update a DB status.
    For this demo, we'll overwrite the 'cold_case_episode.mp3'.
    """
    print(f"🎬 Starting generation for: {case_req.title}")
    
    # 1. Setup Case
    case = CaseFile(
        case_id="generated-limitless",
        title=case_req.title,
        location=case_req.location,
        date_occurred=case_req.date,
        raw_content=case_req.description,
        evidence_list=[] # We could parse this or ask for more inputs
    )
    
    try:
        # 2. Generate Debate
        print("🤖 Generating script...")
        debate_engine = create_debate_engine()
        script = await debate_engine.generate_debate(case, num_exchanges=12)
        
        # 3. Synthesize Audio
        print("🔊 Synthesizing audio...")
        audio_service = create_audio_service()
        audio_segments = []
        
        for line in script.chapters:
            audio_data = await audio_service.synthesize_dialogue(line)
            audio_segments.append(audio_data)
            
        # 4. Save File
        full_episode = b"".join(audio_segments)
        output_path = "frontend/cold_case_episode.mp3"
        with open(output_path, "wb") as f:
            f.write(full_episode)
            
        print(f"✅ Episode ready: {output_path}")
        
    except Exception as e:
        print(f"❌ Generation failed: {e}")

@app.post("/api/generate")
async def generate_episode(request: CaseRequest, background_tasks: BackgroundTasks):
    """Start the generation process in the background."""
    background_tasks.add_task(generate_episode_task, request)
    return {"status": "processing", "message": "Investigative team dispatched. Analysis underway."}

@app.get("/api/cases")
async def get_cases(
    limit: int = Query(50, le=500),
    offset: int = Query(0),
    state: str = Query(None),
    case_type: str = Query(None),
    search: str = Query(None)
):
    """Get cases from the database for the case browser."""
    if not CASE_SELECTOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="Case database not available")
    
    try:
        selector = create_case_selector()
        
        if search:
            cases = selector.search(search, limit=limit)
        else:
            # Build query based on filters
            cases = selector.get_random_unsolved(state=state, limit=limit)
        
        return {"cases": cases, "total": len(cases)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cases/stats")
async def get_case_stats():
    """Get database statistics."""
    if not CASE_SELECTOR_AVAILABLE:
        return {"total_cases": 0, "unsolved_cases": 0, "missing_persons": 0, "states_covered": 0}
    
    try:
        selector = create_case_selector()
        return selector.get_stats()
    except Exception as e:
        return {"total_cases": 0, "unsolved_cases": 0, "error": str(e)}


@app.get("/api/cases/{case_id}")
async def get_case(case_id: str):
    """Get a specific case by ID."""
    if not CASE_SELECTOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="Case database not available")
    
    try:
        selector = create_case_selector()
        case = selector.get_by_id(case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        return case
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/episode")
async def get_episode(request: Request):
    """Get current episode data with proper audio URL for frontend."""
    # Determine the base URL for audio files
    # Use the request's base URL so it works in any environment
    base_url = str(request.base_url).rstrip('/')
    
    # Try to load episode_data.json
    episode_path = "frontend/episode_data.json"
    if os.path.exists(episode_path):
        with open(episode_path, 'r') as f:
            episode_data = json.load(f)
    else:
        episode_data = {
            "case": {
                "title": "No Episode Available",
                "location": "Unknown",
                "date": "Unknown"
            },
            "visualCues": []
        }
    
    # Add the audio URL - use relative path that works through Vercel proxy
    audio_file = "frontend/cold_case_episode.mp3"
    if os.path.exists(audio_file):
        # Use relative path - Vercel will proxy /audio/* to Railway
        episode_data["audioUrl"] = "/audio/cold_case_episode.mp3"
    else:
        episode_data["audioUrl"] = None
    
    return episode_data

# Create audio directory symlink/copy for serving
# Mount audio files at /audio path (more specific, takes precedence)
app.mount("/audio", StaticFiles(directory="frontend"), name="audio")

# Mount frontend files - MUST be last as it catches all routes
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=3000, reload=True)
