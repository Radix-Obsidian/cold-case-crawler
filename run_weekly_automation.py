#!/usr/bin/env python3
"""
Murder Index Weekly Automation Runner

Run this script to generate all weekly content:
- Case of the week selection
- AI analysis (Thorne + Maya)
- Social media posts
- Newsletter content

Usage:
    python run_weekly_automation.py          # Normal run
    python run_weekly_automation.py --force  # Force regenerate
    python run_weekly_automation.py --preview # Preview without generating
"""

import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║           🎙️  MURDER INDEX WEEKLY AUTOMATION                 ║
║                                                              ║
║   Automated content generation for the true crime platform   ║
╚══════════════════════════════════════════════════════════════╝
""")


async def run_automation(force: bool = False, preview: bool = False):
    from src.services.content_automation import (
        run_weekly_pipeline,
        get_weekly_content,
        get_week_id,
        select_case_of_the_week,
        list_generated_weeks
    )
    
    week_id = get_week_id()
    print(f"📅 Current week: {week_id}")
    print(f"📅 Date: {datetime.now().strftime('%B %d, %Y')}")
    print()
    
    # Check existing content
    existing = get_weekly_content(week_id)
    if existing and existing.status == "complete" and not force:
        print(f"✅ Content already generated for {week_id}")
        print(f"   Case: {existing.case_title}")
        print(f"   Generated: {existing.completed_at}")
        print()
        print("Use --force to regenerate")
        return existing
    
    if preview:
        print("🔍 PREVIEW MODE - No content will be generated")
        print()
        
        # Show what would be selected
        case = select_case_of_the_week()
        if case:
            print(f"📋 Would select case:")
            print(f"   Title: {case.get('title')}")
            print(f"   Victim: {case.get('victim', {}).get('name', 'Unknown')}")
            print(f"   Has Photo: {'Yes' if case.get('media') else 'No'}")
            print(f"   Summary: {case.get('summary', '')[:200]}...")
        
        # Show previously generated weeks
        weeks = list_generated_weeks()
        if weeks:
            print(f"\n📚 Previously generated weeks: {len(weeks)}")
            for w in weeks[-5:]:
                print(f"   - {w}")
        
        return None
    
    # Run the full pipeline
    print("🚀 Starting weekly content generation...")
    print()
    
    try:
        content = await run_weekly_pipeline(force_regenerate=force)
        
        print()
        print("=" * 60)
        print("✅ WEEKLY CONTENT GENERATED SUCCESSFULLY")
        print("=" * 60)
        print()
        print(f"📋 Case: {content.case_title}")
        print(f"🆔 Case ID: {content.case_id}")
        print()
        
        # Show analysis preview
        if content.thorne_analysis:
            print("🔬 Dr. Thorne's Assessment (preview):")
            print(f"   {content.thorne_analysis[:200]}...")
            print()
        
        if content.maya_analysis:
            print("🧠 Maya's Profile (preview):")
            print(f"   {content.maya_analysis[:200]}...")
            print()
        
        # Show social media posts
        if content.twitter_post:
            print("📱 Twitter Post:")
            print("-" * 40)
            print(content.twitter_post)
            print("-" * 40)
            print()
        
        # Show key questions
        if content.key_questions:
            print("❓ Key Questions:")
            for q in content.key_questions[:3]:
                print(f"   • {q}")
            print()
        
        print(f"📁 Content saved to: data/weekly_content/{week_id}.json")
        
        return content
        
    except Exception as e:
        print(f"❌ Automation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(description="Murder Index Weekly Automation")
    parser.add_argument("--force", action="store_true", help="Force regenerate even if content exists")
    parser.add_argument("--preview", action="store_true", help="Preview mode - show what would be generated")
    args = parser.parse_args()
    
    print_banner()
    
    result = asyncio.run(run_automation(force=args.force, preview=args.preview))
    
    if result and result.status == "complete":
        print()
        print("🎉 Ready to publish!")
        print("   1. Review content in data/weekly_content/")
        print("   2. Copy social posts to Buffer/Hootsuite")
        print("   3. Send newsletter via your email provider")
        print()


if __name__ == "__main__":
    main()
