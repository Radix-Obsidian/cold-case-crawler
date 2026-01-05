#!/usr/bin/env python3
"""
Create a full Murder Index episode with AI-generated debate and audio.
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from src.models.case import CaseFile, Evidence
from src.models.script import DialogueLine, PodcastScript
from src.services.debate import create_debate_engine
from src.services.audio import create_audio_service

async def create_full_episode():
    """Generate a complete podcast episode."""
    
    print("🎙️  COLD CASE CRAWLER - FULL EPISODE GENERATION")
    print("=" * 55)
    
    # Create a compelling cold case
    case = CaseFile(
        case_id="minnesota-riverside-1987",
        title="The Riverside Park Disappearance",
        location="Minneapolis, Minnesota",
        date_occurred="December 14, 1987",
        raw_content="""
        Sarah Johnson, a 28-year-old nurse at Minneapolis General Hospital, 
        vanished after her night shift on December 14th, 1987. Her car was 
        found three days later in Riverside Park, keys still in the ignition.
        
        The investigation uncovered puzzling details:
        - No signs of struggle in or around the vehicle
        - Her purse was missing, but her jacket remained on the passenger seat
        - A witness reported seeing a man near her car around 11 PM
        - Hospital security cameras were conveniently non-functional that night
        - Sarah had recently ended a relationship with a coworker
        
        Despite extensive searches and over 200 interviews, Sarah was never 
        found. The case went cold in 1992 but was reopened in 2015 when new 
        DNA technology became available. The results were inconclusive.
        
        Sarah's family maintains a website and offers a $50,000 reward for 
        information leading to answers about what happened that December night.
        """,
        evidence_list=[
            Evidence(evidence_id="ev-001", evidence_type="Physical", 
                    description="Abandoned 1985 Honda Civic with keys in ignition"),
            Evidence(evidence_id="ev-002", evidence_type="Witness",
                    description="Male figure seen near vehicle at 11 PM"),
            Evidence(evidence_id="ev-003", evidence_type="Circumstantial",
                    description="Recent breakup with hospital coworker Dr. Mark Stevens"),
        ]
    )
    
    print(f"📋 Case: {case.title}")
    print(f"📍 Location: {case.location}")
    print(f"📅 Date: {case.date_occurred}")
    
    # Step 1: Generate AI debate (3 exchanges = 6 lines, ~2000 chars)
    print("\n🤖 STEP 1: Generating AI debate...")
    debate_engine = create_debate_engine()
    
    try:
        script = await debate_engine.generate_debate(case, num_exchanges=15)
        print(f"✅ Generated {len(script.chapters)} dialogue lines")
        
        # Show the script
        print("\n📜 SCRIPT:")
        print("-" * 40)
        total_chars = 0
        for i, line in enumerate(script.chapters, 1):
            speaker = "MAYA" if line.speaker == "maya_vance" else "DR. THORNE"
            formatted = line.to_elevenlabs_format()
            total_chars += len(formatted)
            print(f"\n{i}. {speaker}:")
            print(f"   {formatted}")
        
        print(f"\n📊 Total characters: {total_chars}")
        
    except Exception as e:
        print(f"❌ Debate generation failed: {e}")
        return
    
    # Step 2: Generate audio for each line
    print("\n🔊 STEP 2: Generating audio...")
    audio_service = create_audio_service()
    
    audio_segments = []
    for i, line in enumerate(script.chapters, 1):
        speaker = "Maya" if line.speaker == "maya_vance" else "Dr. Thorne"
        print(f"  [{i}/{len(script.chapters)}] {speaker}...", end=" ", flush=True)
        
        try:
            audio_data = await audio_service.synthesize_dialogue(line)
            audio_segments.append(audio_data)
            print(f"✅ ({len(audio_data):,} bytes)")
        except Exception as e:
            print(f"❌ {e}")
            return
    
    # Step 3: Combine into single episode
    print("\n🎬 STEP 3: Combining audio...")
    full_episode = b"".join(audio_segments)
    
    filename = "cold_case_episode.mp3"
    with open(filename, "wb") as f:
        f.write(full_episode)
    
    print(f"✅ Saved: {filename}")
    print(f"📦 Size: {len(full_episode):,} bytes ({len(full_episode)//1024} KB)")
    
    print("\n" + "=" * 55)
    print("🎉 EPISODE COMPLETE!")
    print(f"🎧 Play '{filename}' to hear Maya and Dr. Thorne debate!")
    print("=" * 55)

if __name__ == "__main__":
    asyncio.run(create_full_episode())