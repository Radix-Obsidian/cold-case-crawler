#!/usr/bin/env python3
"""
Scrape images for a cold case from various sources.
Downloads images with proper attribution for use in the visual player.
"""

import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv()

from src.services.image_scraper import create_image_scraper


# Cold case image sources - public domain and news archives
CASE_SOURCES = {
    "isdal_woman": [
        "https://en.wikipedia.org/wiki/Isdal_Woman",
        "https://www.bbc.com/news/world-europe-39369429",
    ],
    "zodiac_killer": [
        "https://en.wikipedia.org/wiki/Zodiac_Killer",
    ],
    "black_dahlia": [
        "https://en.wikipedia.org/wiki/Black_Dahlia",
    ],
    "db_cooper": [
        "https://en.wikipedia.org/wiki/D._B._Cooper",
    ],
    "jonbenet_ramsey": [
        "https://en.wikipedia.org/wiki/Killing_of_JonBen%C3%A9t_Ramsey",
    ],
}

# Uncovered.com and other cold case databases
COLD_CASE_DATABASES = [
    "https://uncovered.com",
    "https://charleyproject.org",
    "https://www.doenetwork.org",
]


async def scrape_wikipedia_case(case_name: str):
    """Scrape images from Wikipedia for a famous cold case."""
    print(f"🔍 Scraping images for: {case_name}")
    
    scraper = create_image_scraper()
    
    if case_name in CASE_SOURCES:
        urls = CASE_SOURCES[case_name]
    else:
        # Try Wikipedia search
        urls = [f"https://en.wikipedia.org/wiki/{case_name.replace(' ', '_')}"]
    
    images = await scraper.scrape_and_download(urls, limit_per_url=8)
    
    print(f"\n✅ Downloaded {len(images)} images:")
    for img in images:
        print(f"   [{img.image_type:10}] {img.local_path}")
        print(f"              Attribution: {img.attribution}")
    
    return images


async def scrape_for_current_episode():
    """Scrape images for the current episode based on episode_data.json."""
    
    # Load current episode data
    try:
        with open("frontend/episode_data.json", "r") as f:
            episode_data = json.load(f)
    except FileNotFoundError:
        print("❌ No episode_data.json found. Generate an episode first.")
        return
    
    case = episode_data.get("case", {})
    print(f"📋 Case: {case.get('title', 'Unknown')}")
    print(f"📍 Location: {case.get('location', 'Unknown')}")
    
    scraper = create_image_scraper()
    
    # Try to scrape from source URLs
    source_urls = case.get("sources", [])
    if source_urls:
        print(f"\n🌐 Scraping from {len(source_urls)} source URLs...")
        images = await scraper.scrape_and_download(source_urls, limit_per_url=5)
    else:
        # Search for related images
        print("\n🔍 No source URLs, searching Wikipedia...")
        title = case.get("title", "").lower()
        
        # Try to find related Wikipedia articles
        search_terms = [
            case.get("title", "cold case"),
            case.get("location", ""),
        ]
        
        urls = []
        for term in search_terms:
            if term:
                wiki_url = f"https://en.wikipedia.org/wiki/{term.replace(' ', '_')}"
                urls.append(wiki_url)
        
        images = await scraper.scrape_and_download(urls[:3], limit_per_url=5)
    
    if images:
        print(f"\n✅ Downloaded {len(images)} images")
        
        # Update episode_data.json with images
        episode_data["case"]["images"] = [
            {
                "id": img.image_id,
                "path": img.local_path,
                "type": img.image_type,
                "caption": img.caption or img.alt_text,
                "attribution": img.attribution,
            }
            for img in images
        ]
        
        with open("frontend/episode_data.json", "w") as f:
            json.dump(episode_data, f, indent=2)
        
        print("✅ Updated episode_data.json with images")
    else:
        print("⚠️  No images found")
    
    return images


async def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) > 1:
        case_name = sys.argv[1]
        await scrape_wikipedia_case(case_name)
    else:
        # Default: scrape for current episode
        await scrape_for_current_episode()


if __name__ == "__main__":
    asyncio.run(main())
