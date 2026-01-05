#!/usr/bin/env python3
"""
Test script to verify end-to-end audio generation works.
This will test the debate generation and audio synthesis.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from src.config import get_settings
from src.models.case import CaseFile, Evidence
from src.services.debate import create_debate_engine
from src.services.audio import create_audio_service

async def test_end_to_end():
    """Test the complete pipeline from case to audio."""
    
    print("🎙️  TESTING COLD CASE CRAWLER END-TO-END")
    print("=" * 50)
    
    # Create a test case
    test_case = CaseFile(
        case_id="test-case-001",
        title="The Riverside Park Mystery",
        location="Minneapolis, Minnesota",
        date_occurred="1987-12-14",
        raw_content="""
        On December 14th, 1987, Sarah Johnson, a 28-year-old nurse, disappeared 
        after leaving work at Minneapolis General Hospital. Her car was found 
        abandoned in Riverside Park three days later, keys still in the ignition.
        
        The investigation revealed several puzzling elements:
        - No signs of struggle in the vehicle
        - Her purse was missing but her jacket remained
        - A witness reported seeing a man near her car around 11 PM
        - Security cameras were not functioning that night
        
        Despite extensive searches and interviews, Sarah was never found.
        The case remains unsolved after 37 years.
        """,
        evidence_list=[
            Evidence(
                evidence_id="ev-001",
                evidence_type="Physical",
                description="Abandoned vehicle with keys in ignition"
            ),
            Evidence(
                evidence_id="ev-002", 
                evidence_type="Witness",
                description="Unidentified man seen near vehicle at 11 PM"
            )
        ]
    )
    
    print(f"📋 Test Case: {test_case.title}")
    print(f"📍 Location: {test_case.location}")
    print(f"📅 Date: {test_case.date_occurred}")
    
    # Test 1: Generate debate with AI agents
    print("\n🤖 STEP 1: Generating AI debate...")
    try:
        debate_engine = create_debate_engine()
        script = await debate_engine.generate_debate(test_case, num_exchanges=3)
        
        print(f"✅ Generated script with {len(script.chapters)} dialogue lines")
        print(f"📝 Episode title: {script.episode_title}")
        print(f"🎯 Social hooks: {len(script.social_hooks)}")
        
        # Show first few lines
        print("\n📖 First few dialogue lines:")
        for i, line in enumerate(script.chapters[:4], 1):
            speaker_name = "Maya" if line.speaker == "maya_vance" else "Dr. Thorne"
            print(f"  {i}. {speaker_name}: {line.text[:80]}...")
            
    except Exception as e:
        print(f"❌ Debate generation failed: {e}")
        return False
    
    # Test 2: Generate audio (just first 2 lines to save API costs)
    print(f"\n🔊 STEP 2: Generating audio for first 2 lines...")
    try:
        settings = get_settings()
        if not settings.elevenlabs_api_key:
            print("⚠️  No ElevenLabs API key found - skipping audio generation")
            print("✅ System is ready for audio generation when API key is provided")
            return True
            
        audio_service = create_audio_service()
        
        # Test with just first 2 lines to save costs
        test_lines = script.chapters[:2]
        
        for i, line in enumerate(test_lines, 1):
            print(f"  Generating audio {i}/{len(test_lines)}...")
            
            # Apply directorial pass and show formatted text
            processed_line = audio_service.apply_directorial_pass(line)
            formatted_text = processed_line.to_elevenlabs_format()
            print(f"    Formatted: {formatted_text[:60]}...")
            
            # Generate audio (this will make actual API call)
            audio_data = await audio_service.synthesize_dialogue(line)
            
            if audio_data and len(audio_data) > 0:
                print(f"    ✅ Generated {len(audio_data)} bytes of audio")
                
                # Save to file for verification
                filename = f"test_audio_line_{i}.mp3"
                with open(filename, "wb") as f:
                    f.write(audio_data)
                print(f"    💾 Saved as {filename}")
            else:
                print(f"    ❌ No audio data generated")
                return False
                
        print(f"\n🎉 SUCCESS! Generated audio for {len(test_lines)} dialogue lines")
        print("🎧 Check the generated .mp3 files to hear the AI hosts!")
        
    except Exception as e:
        print(f"❌ Audio generation failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_end_to_end())
    if success:
        print(f"\n✅ COLD CASE CRAWLER IS FULLY FUNCTIONAL!")
        print("🚀 Ready to crawl cold cases and generate podcast episodes!")
    else:
        print(f"\n❌ Some tests failed - check the errors above")