#!/usr/bin/env python3
"""
Run Charley Project scraper and save cases to JSON for frontend.
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent))

from data_pipeline.scrapers.charley_scraper import scrape_charley_project
from data_pipeline.config import IMAGES_DIR

OUTPUT_FILE = Path("frontend/charley_cases.json")


async def main():
    print("=" * 60)
    print("🔍 MURDER INDEX - Charley Project Data Collection")
    print("=" * 60)
    print()
    
    # Scrape cases (start with 150 to get good variety)
    cases = await scrape_charley_project(
        images_dir=IMAGES_DIR,
        max_cases=150,
        download_images=False  # Use remote URLs for now
    )
    
    if not cases:
        print("❌ No cases scraped!")
        return
    
    # Filter to cases with good data
    good_cases = []
    for case in cases:
        # Must have name and some content
        if case.get('victim', {}).get('name') and case.get('summary'):
            # Add media array if photo exists
            photo_url = case.get('victim', {}).get('photo_url')
            if photo_url:
                case['media'] = [{
                    'url': photo_url,
                    'thumbnail': photo_url,
                    'type': 'victim_photo',
                    'caption': f"Photo of {case['victim']['name']}"
                }]
                case['media_attribution'] = 'Photo: The Charley Project'
            
            good_cases.append(case)
    
    print(f"\n📊 Stats:")
    print(f"   Total scraped: {len(cases)}")
    print(f"   With good data: {len(good_cases)}")
    print(f"   With photos: {len([c for c in good_cases if c.get('media')])}")
    
    # Save to JSON
    output_data = {
        'cases': good_cases,
        'source': 'The Charley Project',
        'source_url': 'https://charleyproject.org',
        'scraped_at': datetime.utcnow().isoformat(),
        'total_cases': len(good_cases),
        'attribution': 'Data compiled from The Charley Project (charleyproject.org). Used with permission per their FAQ.'
    }
    
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output_data, f, indent=2, default=str)
    
    print(f"\n✅ Saved {len(good_cases)} cases to {OUTPUT_FILE}")
    
    # Show sample
    if good_cases:
        sample = good_cases[0]
        print(f"\n📋 Sample case:")
        print(f"   Name: {sample['victim'].get('name')}")
        print(f"   Location: {sample.get('city')}, {sample.get('state')}")
        print(f"   Date: {sample.get('date_occurred')}")
        print(f"   Has Photo: {'Yes' if sample.get('media') else 'No'}")


if __name__ == "__main__":
    asyncio.run(main())
