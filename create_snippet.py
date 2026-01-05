#!/usr/bin/env python3
"""
Create a tiny snippet episode using minimal ElevenLabs credits.
With only 10 credits remaining, we need very short text (~10 characters max).
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from src.models.script import DialogueLine
from src.services.audio import create_audio_service

async def create_snippet():
    """Create a tiny audio snippet."""
    
    print("🎙️  CREATING SNIPPET EPISODE")
    print("=" * 40)
    
    # Super short lines to fit in 10 credits
    # Each character = ~1 credit, so we need < 10 chars
    snippet = DialogueLine(
        speaker="dr_aris_thorne",
        text="Hello.",
        emotion_tag="neutral"
    )
    
    print(f"📝 Text: '{snippet.text}' ({len(snippet.text)} chars)")
    
    audio_service = create_audio_service()
    
    try:
        print("🔊 Generating audio...")
        audio_data = await audio_service.synthesize_dialogue(snippet)
        
        if audio_data:
            filename = "snippet_episode.mp3"
            with open(filename, "wb") as f:
                f.write(audio_data)
            print(f"✅ Saved: {filename} ({len(audio_data)} bytes)")
            print("🎧 Play the file to hear Dr. Thorne!")
        else:
            print("❌ No audio generated")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Your ElevenLabs credits may be exhausted.")
        print("   Check your account at elevenlabs.io")

if __name__ == "__main__":
    asyncio.run(create_snippet())