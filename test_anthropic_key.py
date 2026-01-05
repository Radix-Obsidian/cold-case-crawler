#!/usr/bin/env python3
"""
Simple test to verify Anthropic API key works.
"""

import os
import asyncio
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()

async def test_anthropic_key():
    """Test if the Anthropic API key works."""
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in .env")
        return False
    
    print("🔑 Testing Anthropic API Key...")
    
    try:
        client = AsyncAnthropic(api_key=api_key)
        
        # Try to make a simple request
        response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=50,
            messages=[
                {"role": "user", "content": "Say hello in one sentence."}
            ]
        )
        
        print(f"✅ API Key works! Response: {response.content[0].text}")
        return True
        
    except Exception as e:
        print(f"❌ API Key test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_anthropic_key())
    if success:
        print("🎉 Anthropic API key is working correctly!")
    else:
        print("💥 There's an issue with the Anthropic API key or model name.")