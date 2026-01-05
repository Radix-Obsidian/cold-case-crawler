#!/usr/bin/env python3
"""
Create a Cold Case Crawler episode from REAL cold case data.
Exports timestamps and visual cues for the frontend.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import List
from dotenv import load_dotenv
from mutagen.mp3 import MP3
import io

load_dotenv()

from src.models.case import CaseFile, Evidence
from src.models.script import DialogueLine, PodcastScript
from src.services.debate import create_debate_engine
from src.services.audio import create_audio_service
from src.services.crawler import create_crawler_service
from src.services.image_scraper import create_image_scraper, CaseImage


async def fetch_real_case(query: str = "cold case unsolved murder") -> CaseFile:
    """Fetch a real cold case from web sources."""
    print("🔍 Searching for real cold cases...")
    
    crawler = create_crawler_service()
    
    try:
        cases = await crawler.search_cold_cases(query, limit=3)
        if cases:
            case = cases[0]
            print(f"✅ Found: {case.title}")
            print(f"   Location: {case.location}")
            print(f"   Date: {case.date_occurred or 'Unknown'}")
            return case
    except Exception as e:
        print(f"⚠️  Crawler error: {e}")
    
    # Fallback to a well-documented real case
    print("📋 Using documented case: The Isdal Woman")
    return CaseFile(
        case_id="isdal-woman-1970",
        title="The Isdal Woman",
        location="Bergen, Norway",
        date_occurred="November 29, 1970",
        raw_content="""
        On November 29, 1970, a university professor hiking in Isdalen Valley 
        near Bergen, Norway discovered the partially burned body of a woman.
        
        The investigation revealed extraordinary details:
        - All labels had been cut from her clothing
        - Her fingerprints had been sanded off
        - She carried multiple passports with different identities
        - Coded notes were found in her luggage
        - She had checked into hotels under 8 different names
        - Witnesses described her speaking multiple languages fluently
        - A suitcase linked to her contained wigs and disguises
        
        The autopsy revealed she died from a combination of carbon monoxide 
        poisoning and sleeping pills. Her front teeth had been removed, 
        possibly to prevent dental identification.
        
        Theories range from Cold War espionage to organized crime. Despite 
        decades of investigation and DNA analysis, her identity remains unknown.
        She is buried in Bergen under a headstone that simply reads "Unknown."
        
        In 2017, investigators released a facial reconstruction hoping someone 
        might recognize her. The case remains one of Norway's greatest mysteries.
        """,
        evidence_list=[
            Evidence(evidence_id="ev-001", evidence_type="Physical",
                    description="Partially burned body with removed fingerprints"),
            Evidence(evidence_id="ev-002", evidence_type="Documentary",
                    description="Multiple passports with different identities"),
            Evidence(evidence_id="ev-003", evidence_type="Physical",
                    description="Coded notes and encryption materials"),
            Evidence(evidence_id="ev-004", evidence_type="Circumstantial",
                    description="Wigs, disguises, and spy-like equipment"),
        ],
        source_urls=[
            "https://en.wikipedia.org/wiki/Isdal_Woman",
            "https://www.bbc.com/news/world-europe-39369429"
        ]
    )


def get_audio_duration(audio_data: bytes) -> float:
    """Get duration of MP3 audio in seconds."""
    try:
        audio_file = io.BytesIO(audio_data)
        audio = MP3(audio_file)
        return audio.info.length
    except Exception:
        # Estimate based on typical speech rate (~150 words/min, ~10 chars/sec)
        return len(audio_data) / 15000  # Rough estimate


async def create_real_episode():
    """Generate episode from real case with accurate timestamps."""
    
    print("🎙️  COLD CASE CRAWLER - REAL CASE EPISODE")
    print("=" * 60)
    
    # Step 1: Get real case data
    case = await fetch_real_case()
    
    print(f"\n📋 CASE FILE")
    print(f"   Title: {case.title}")
    print(f"   Location: {case.location}")
    print(f"   Date: {case.date_occurred}")
    print(f"   Evidence items: {len(case.evidence_list)}")
    
    # Step 1.5: Scrape images from case sources
    print("\n🖼️  SCRAPING CASE IMAGES...")
    image_scraper = create_image_scraper()
    case_images: List[CaseImage] = []
    
    if case.source_urls:
        case_images = await image_scraper.scrape_and_download(
            case.source_urls, 
            limit_per_url=5
        )
        print(f"✅ Downloaded {len(case_images)} images")
        for img in case_images:
            print(f"   - [{img.image_type}] {img.local_path}")
    else:
        print("⚠️  No source URLs for image scraping")
    
    # Step 2: Generate AI debate
    print("\n🤖 GENERATING DEBATE...")
    debate_engine = create_debate_engine()
    
    try:
        script = await debate_engine.generate_debate(case, num_exchanges=6)
        print(f"✅ Generated {len(script.chapters)} dialogue lines")
    except Exception as e:
        print(f"❌ Debate generation failed: {e}")
        raise
    
    # Step 3: Generate audio with timestamps
    print("\n🔊 GENERATING AUDIO WITH TIMESTAMPS...")
    audio_service = create_audio_service()
    
    audio_segments = []
    visual_cues = []
    current_time = 0.0
    
    for i, line in enumerate(script.chapters):
        speaker_name = "Maya" if line.speaker == "maya_vance" else "Dr. Thorne"
        print(f"  [{i+1}/{len(script.chapters)}] {speaker_name}...", end=" ", flush=True)
        
        try:
            audio_data = await audio_service.synthesize_dialogue(line)
            duration = get_audio_duration(audio_data)
            
            # Create visual cue with accurate timestamp
            cue = {
                "time": round(current_time, 2),
                "duration": round(duration, 2),
                "speaker": "maya" if line.speaker == "maya_vance" else "thorne",
                "text": line.text,
                "emotion": line.emotion_tag,
            }
            
            # Add scene/evidence based on content
            text_lower = line.text.lower()
            if any(word in text_lower for word in ["evidence", "found", "discovered", "body"]):
                cue["showEvidence"] = True
                if case.evidence_list:
                    cue["evidenceText"] = case.evidence_list[i % len(case.evidence_list)].description
            
            if i == 0:  # First line shows location
                cue["showLocation"] = True
                cue["location"] = case.location
                cue["date"] = case.date_occurred
            
            visual_cues.append(cue)
            audio_segments.append(audio_data)
            current_time += duration
            
            print(f"✅ {duration:.1f}s")
            
        except Exception as e:
            print(f"❌ {e}")
            raise
    
    # Step 4: Combine audio
    print("\n🎬 COMBINING AUDIO...")
    full_episode = b"".join(audio_segments)
    
    # Save audio
    audio_filename = "frontend/cold_case_episode.mp3"
    with open(audio_filename, "wb") as f:
        f.write(full_episode)
    print(f"✅ Audio saved: {audio_filename}")
    
    # Also save to root for backwards compatibility
    with open("cold_case_episode.mp3", "wb") as f:
        f.write(full_episode)
    
    # Step 5: Export episode data for frontend
    episode_data = {
        "case": {
            "id": case.case_id,
            "title": case.title,
            "location": case.location,
            "date": case.date_occurred,
            "summary": case.raw_content[:500] + "..." if len(case.raw_content) > 500 else case.raw_content,
            "evidence": [
                {"id": e.evidence_id, "type": e.evidence_type, "description": e.description}
                for e in case.evidence_list
            ],
            "sources": case.source_urls,
            "images": [
                {
                    "id": img.image_id,
                    "path": img.local_path,
                    "type": img.image_type,
                    "caption": img.caption or img.alt_text,
                    "attribution": img.attribution,
                }
                for img in case_images
            ],
        },
        "audio": {
            "filename": "cold_case_episode.mp3",
            "duration": round(current_time, 2),
            "generated": datetime.now().isoformat(),
        },
        "visualCues": visual_cues,
        "transcript": [
            {
                "speaker": "maya" if line.speaker == "maya_vance" else "thorne",
                "text": line.text,
                "emotion": line.emotion_tag,
            }
            for line in script.chapters
        ]
    }
    
    # Save episode data
    data_filename = "frontend/episode_data.json"
    with open(data_filename, "w") as f:
        json.dump(episode_data, f, indent=2)
    print(f"✅ Episode data saved: {data_filename}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("🎉 EPISODE COMPLETE!")
    print(f"   📋 Case: {case.title}")
    print(f"   🎧 Audio: {len(full_episode):,} bytes ({current_time:.1f}s)")
    print(f"   📊 Visual cues: {len(visual_cues)}")
    print("=" * 60)
    
    return episode_data


if __name__ == "__main__":
    asyncio.run(create_real_episode())
