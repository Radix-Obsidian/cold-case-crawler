"""Scrape Virginia Cold Case database - includes images!"""
import asyncio
import aiohttp
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


VIRGINIA_CSV_URL = "https://data.virginia.gov/dataset/373adf97-0f5e-43c0-8fcb-acec5112f4e3/resource/1b5aa115-a3fc-4f74-9a2f-c174c53cb5a2/download/ccdb-12-23-2025-prod-2.csv"
VIRGINIA_COLD_CASE_SITE = "https://coldcase.vsp.virginia.gov"


async def fetch_virginia_cases_csv() -> List[Dict]:
    """Fetch Virginia cases from CSV download."""
    import pandas as pd
    import io
    
    print("📥 Downloading Virginia Cold Case CSV...")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(VIRGINIA_CSV_URL) as response:
            if response.status == 200:
                content = await response.text()
                df = pd.read_csv(io.StringIO(content))
                cases = df.to_dict('records')
                print(f"✅ Loaded {len(cases)} Virginia cases from CSV")
                return cases
            else:
                print(f"❌ Error downloading Virginia CSV: {response.status}")
                return []


async def fetch_all_virginia_cases() -> List[Dict]:
    """Fetch all cases from Virginia CSV."""
    return await fetch_virginia_cases_csv()


async def download_image(session: aiohttp.ClientSession, url: str, save_path: Path) -> bool:
    """Download an image to local storage."""
    try:
        async with session.get(url, timeout=30) as response:
            if response.status == 200:
                content = await response.read()
                save_path.parent.mkdir(parents=True, exist_ok=True)
                save_path.write_bytes(content)
                return True
    except Exception as e:
        print(f"   ⚠️ Failed to download {url}: {e}")
    return False


def generate_case_id(case: Dict) -> str:
    """Generate unique ID for Virginia case."""
    key = f"va-{case.get('case_number', '')}-{case.get('name', '')}"
    return hashlib.md5(key.encode()).hexdigest()[:16]


def normalize_virginia_case(case: Dict, images_dir: Path) -> Dict[str, Any]:
    """Convert Virginia CSV data to our schema."""
    
    # Handle both lowercase and Title Case column names from CSV
    def get_val(key: str):
        return case.get(key) or case.get(key.title()) or case.get(key.upper()) or case.get(key.lower())
    
    # Parse date - try multiple column names
    date_str = safe_str(get_val('date_missing') or get_val('Date Missing') or 
                        get_val('date_of_death') or get_val('Date of Death') or
                        get_val('incident_date') or get_val('Incident Date'))
    date_occurred = None
    if date_str:
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y-%m-%dT%H:%M:%S', '%B %d, %Y']:
            try:
                date_occurred = datetime.strptime(date_str.split('T')[0], fmt).date()
                break
            except:
                continue
    
    # Determine case type
    case_type_val = safe_str(get_val('case_type') or get_val('Case Type') or get_val('type'))
    case_type = 'missing_person'
    if case_type_val:
        ct = case_type_val.lower()
        if 'homicide' in ct or 'murder' in ct:
            case_type = 'homicide'
        elif 'unidentified' in ct:
            case_type = 'unidentified'
    
    # Get name
    name = safe_str(get_val('name') or get_val('Name') or get_val('victim_name')) or 'Unknown'
    
    # Build victim info
    victim = {
        'name': name,
        'age': parse_age_range(get_val('age') or get_val('Age')),
        'gender': safe_str(get_val('sex') or get_val('Sex') or get_val('gender')).lower() or 'unknown',
        'race': safe_str(get_val('race') or get_val('Race')),
        'height': safe_str(get_val('height') or get_val('Height')),
        'weight': safe_str(get_val('weight') or get_val('Weight')),
        'hair_color': safe_str(get_val('hair') or get_val('Hair') or get_val('hair_color')),
        'eye_color': safe_str(get_val('eyes') or get_val('Eyes') or get_val('eye_color')),
        'photo_url': safe_str(get_val('image_url') or get_val('photo') or get_val('Photo URL')),
    }
    
    case_number = safe_str(get_val('case_number') or get_val('Case Number') or get_val('id'))
    
    normalized = {
        'case_id': generate_case_id(case),
        'title': f"{name} - {case_type_val or 'Cold Case'}",
        'case_type': case_type,
        'status': 'unsolved',
        'date_occurred': str(date_occurred) if date_occurred else None,
        'city': safe_str(get_val('city') or get_val('City')),
        'county': safe_str(get_val('county') or get_val('County')),
        'state': 'Virginia',
        'country': 'USA',
        'summary': build_virginia_summary(case),
        'source_dataset': 'virginia_cold_case',
        'source_url': f"{VIRGINIA_COLD_CASE_SITE}/case/{case_number}" if case_number else VIRGINIA_COLD_CASE_SITE,
        'raw_data': {k: safe_str(v) for k, v in case.items()},  # Convert all values to strings
        'victim': victim,
        'evidence': extract_virginia_evidence(case),
    }
    
    return normalized


def parse_age_range(age_str) -> Optional[int]:
    """Parse age from various formats."""
    if not age_str:
        return None
    try:
        # Handle ranges like "25-30"
        if '-' in str(age_str):
            parts = str(age_str).split('-')
            return int(parts[0])
        return int(age_str)
    except:
        return None


def safe_str(val) -> str:
    """Convert value to string, handling NaN/None."""
    import pandas as pd
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ''
    return str(val)


def build_virginia_summary(case: Dict) -> str:
    """Build narrative summary for Virginia case."""
    import pandas as pd
    parts = []
    
    name = safe_str(case.get('name')) or safe_str(case.get('Name')) or 'An individual'
    parts.append(f"{name}")
    
    if case.get('date_missing') or case.get('Date Missing'):
        parts.append(f"went missing")
    elif case.get('date_of_death') or case.get('Date of Death'):
        parts.append(f"was found deceased")
    
    location_parts = []
    city = safe_str(case.get('city') or case.get('City'))
    county = safe_str(case.get('county') or case.get('County'))
    if city:
        location_parts.append(city)
    if county:
        location_parts.append(f"{county} County")
    location_parts.append("Virginia")
    
    # Filter out empty strings
    location_parts = [p for p in location_parts if p]
    if location_parts:
        parts.append(f"in {', '.join(location_parts)}.")
    
    circumstances = safe_str(case.get('circumstances') or case.get('Circumstances'))
    if circumstances:
        parts.append(circumstances)
    
    agency = safe_str(case.get('agency') or case.get('Agency'))
    if agency:
        parts.append(f"Investigating agency: {agency}.")
    
    return ' '.join(parts)


def extract_virginia_evidence(case: Dict) -> List[Dict]:
    """Extract evidence items from Virginia case data."""
    evidence = []
    
    if case.get('clothing_description'):
        evidence.append({
            'type': 'physical',
            'description': f"Clothing: {case['clothing_description']}"
        })
    
    if case.get('vehicle_description'):
        evidence.append({
            'type': 'physical',
            'description': f"Vehicle: {case['vehicle_description']}"
        })
    
    if case.get('distinguishing_marks'):
        evidence.append({
            'type': 'physical',
            'description': f"Distinguishing marks: {case['distinguishing_marks']}"
        })
    
    if case.get('circumstances'):
        evidence.append({
            'type': 'circumstantial',
            'description': case['circumstances']
        })
    
    return evidence


async def process_virginia_cases(images_dir: Path, download_images: bool = True) -> List[Dict[str, Any]]:
    """Full pipeline: fetch, normalize, download images."""
    print("\n🔍 Fetching Virginia Cold Cases...")
    
    raw_cases = await fetch_all_virginia_cases()
    
    if not raw_cases:
        print("❌ No cases fetched")
        return []
    
    # Normalize all cases
    normalized = []
    for case in raw_cases:
        normalized.append(normalize_virginia_case(case, images_dir))
    
    # Download images if requested
    if download_images:
        print("\n🖼️ Downloading case images...")
        async with aiohttp.ClientSession() as session:
            for i, case in enumerate(normalized):
                if case['victim'].get('photo_url'):
                    url = case['victim']['photo_url']
                    filename = f"va_{case['case_id']}.jpg"
                    save_path = images_dir / "virginia" / filename
                    
                    if await download_image(session, url, save_path):
                        case['victim']['photo_local_path'] = str(save_path)
                        
                if i > 0 and i % 50 == 0:
                    print(f"   Downloaded {i} images...")
    
    print(f"✅ Processed {len(normalized)} Virginia cases")
    return normalized


if __name__ == "__main__":
    from data_pipeline.config import IMAGES_DIR
    
    cases = asyncio.run(process_virginia_cases(IMAGES_DIR, download_images=False))
    if cases:
        print(f"\nSample case:\n{json.dumps(cases[0], indent=2, default=str)}")
