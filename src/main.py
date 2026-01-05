from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
import asyncio
from typing import Optional

# Import our services
from src.models.case import CaseFile, Evidence
from src.services.debate import create_debate_engine
from src.services.audio import create_audio_service

# Import API routers
from src.api.membership import router as membership_router

app = FastAPI(title="Cold Case Crawler API")

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

# Mount frontend files
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=3000, reload=True)
