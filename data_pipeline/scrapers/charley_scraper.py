"""Scrape Charley Project for missing persons data with rich details."""
import asyncio
import aiohttp
import hashlib
import re
from bs4 import BeautifulSoup
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urljoin


CHARLEY_BASE_URL = "https://charleyproject.org"
CHARLEY_CASES_URL = f"{CHARLEY_BASE_URL}/cases"


async def fetch_page(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    """Fetch a page with rate limiting."""
    try:
        async with session.get(url, timeout=30) as response:
            if response.status == 200:
                return await response.text()
            else:
                print(f"   ⚠️ Status {response.status} for {url}")
    except Exception as e:
        print(f"   ❌ Error fetching {url}: {e}")
    return None


async def get_state_urls(session: aiohttp.ClientSession) -> List[str]:
    """Get all state category URLs from Charley Project."""
    html = await fetch_page(session, CHARLEY_CASES_URL)
    if not html:
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    state_links = []
    
    # Find state links in the cases page
    for link in soup.find_all('a', href=True):
        href = link['href']
        if '/cases/' in href and href != '/cases/':
            full_url = urljoin(CHARLEY_BASE_URL, href)
            if full_url not in state_links:
                state_links.append(full_url)
    
    print(f"📍 Found {len(state_links)} state/category pages")
    return state_links[:10]  # Limit for initial testing


async def get_case_urls_from_state(session: aiohttp.ClientSession, state_url: str) -> List[str]:
    """Get all case URLs from a state page."""
    html = await fetch_page(session, state_url)
    if not html:
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    case_links = []
    
    for link in soup.find_all('a', href=True):
        href = link['href']
        # Case URLs typically look like /case/firstname-lastname
        if '/case/' in href:
            full_url = urljoin(CHARLEY_BASE_URL, href)
            if full_url not in case_links:
                case_links.append(full_url)
    
    return case_links


async def scrape_case_page(session: aiohttp.ClientSession, url: str) -> Optional[Dict]:
    """Scrape detailed info from a single case page."""
    html = await fetch_page(session, url)
    if not html:
        return None
    
    soup = BeautifulSoup(html, 'html.parser')
    
    case_data = {
        'source_url': url,
        'scraped_at': datetime.utcnow().isoformat()
    }
    
    # Extract name from title or h1
    title = soup.find('h1')
    if title:
        case_data['name'] = title.get_text(strip=True)
    
    # Extract main image
    img = soup.find('img', class_='case-photo') or soup.find('img', alt=re.compile(r'photo|image', re.I))
    if img and img.get('src'):
        case_data['photo_url'] = urljoin(CHARLEY_BASE_URL, img['src'])
    
    # Extract case details from definition lists or tables
    for dl in soup.find_all('dl'):
        dt_elements = dl.find_all('dt')
        dd_elements = dl.find_all('dd')
        for dt, dd in zip(dt_elements, dd_elements):
            key = dt.get_text(strip=True).lower().replace(':', '').replace(' ', '_')
            value = dd.get_text(strip=True)
            case_data[key] = value
    
    # Try to extract from table format as well
    for table in soup.find_all('table'):
        for row in table.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True).lower().replace(':', '').replace(' ', '_')
                value = cells[1].get_text(strip=True)
                if key and value:
                    case_data[key] = value
    
    # Extract main content/circumstances
    content_div = soup.find('div', class_='case-content') or soup.find('article')
    if content_div:
        paragraphs = content_div.find_all('p')
        case_data['circumstances'] = ' '.join(p.get_text(strip=True) for p in paragraphs[:5])
    
    return case_data if case_data.get('name') else None


def generate_charley_case_id(case: Dict) -> str:
    """Generate unique ID for Charley case."""
    key = f"charley-{case.get('name', '')}-{case.get('source_url', '')}"
    return hashlib.md5(key.encode()).hexdigest()[:16]


def normalize_charley_case(case: Dict) -> Dict[str, Any]:
    """Convert Charley Project data to our schema."""
    
    # Parse date
    date_str = case.get('date_missing') or case.get('missing_since') or case.get('last_seen')
    date_occurred = None
    if date_str:
        # Try various date formats
        for fmt in ['%B %d, %Y', '%m/%d/%Y', '%Y-%m-%d', '%d %B %Y']:
            try:
                date_occurred = datetime.strptime(date_str, fmt).date()
                break
            except:
                continue
    
    # Parse age
    age = None
    age_str = case.get('age') or case.get('age_at_disappearance') or case.get('age_when_missing')
    if age_str:
        try:
            age = int(re.search(r'\d+', str(age_str)).group())
        except:
            pass
    
    # Parse location
    location = case.get('location') or case.get('last_seen_location') or case.get('missing_from') or ''
    city = None
    state = None
    if ',' in location:
        parts = location.split(',')
        city = parts[0].strip()
        state = parts[-1].strip() if len(parts) > 1 else None
    
    normalized = {
        'case_id': generate_charley_case_id(case),
        'title': f"{case.get('name', 'Unknown')} - Missing Person",
        'case_type': 'missing_person',
        'status': 'unsolved',
        'date_occurred': str(date_occurred) if date_occurred else None,
        'city': city,
        'state': state,
        'country': 'USA',
        'summary': case.get('circumstances', ''),
        'source_dataset': 'charley_project',
        'source_url': case.get('source_url'),
        'raw_data': case,
        'victim': {
            'name': case.get('name'),
            'age': age,
            'gender': case.get('sex', case.get('gender', 'unknown')).lower(),
            'race': case.get('race') or case.get('ethnicity'),
            'height': case.get('height'),
            'weight': case.get('weight'),
            'hair_color': case.get('hair') or case.get('hair_color'),
            'eye_color': case.get('eyes') or case.get('eye_color'),
            'photo_url': case.get('photo_url'),
            'distinguishing_marks': case.get('distinguishing_characteristics') or case.get('identifying_characteristics'),
        },
        'evidence': extract_charley_evidence(case),
    }
    
    return normalized


def extract_charley_evidence(case: Dict) -> List[Dict]:
    """Extract evidence items from Charley case."""
    evidence = []
    
    if case.get('clothing'):
        evidence.append({
            'type': 'physical',
            'description': f"Last seen wearing: {case['clothing']}"
        })
    
    if case.get('vehicle'):
        evidence.append({
            'type': 'physical',
            'description': f"Vehicle: {case['vehicle']}"
        })
    
    if case.get('dental') or case.get('dental_records'):
        evidence.append({
            'type': 'forensic',
            'description': f"Dental records available"
        })
    
    if case.get('dna'):
        evidence.append({
            'type': 'forensic',
            'description': f"DNA: {case['dna']}"
        })
    
    return evidence


async def download_image(session: aiohttp.ClientSession, url: str, save_path: Path) -> bool:
    """Download image to local storage."""
    try:
        async with session.get(url, timeout=30) as response:
            if response.status == 200:
                content = await response.read()
                save_path.parent.mkdir(parents=True, exist_ok=True)
                save_path.write_bytes(content)
                return True
    except Exception as e:
        pass
    return False


async def scrape_charley_project(
    images_dir: Path, 
    max_cases: int = 500,
    download_images: bool = True
) -> List[Dict[str, Any]]:
    """Full pipeline: discover cases, scrape details, download images."""
    print("\n🔍 Scraping Charley Project...")
    
    all_cases = []
    
    async with aiohttp.ClientSession(
        headers={'User-Agent': 'ColdCaseCrawler/1.0 (Research Project)'}
    ) as session:
        
        # Get state/category pages
        state_urls = await get_state_urls(session)
        
        # Collect case URLs from each state
        all_case_urls = []
        for state_url in state_urls:
            case_urls = await get_case_urls_from_state(session, state_url)
            all_case_urls.extend(case_urls)
            await asyncio.sleep(0.5)  # Rate limiting
            
            if len(all_case_urls) >= max_cases:
                break
        
        all_case_urls = list(set(all_case_urls))[:max_cases]
        print(f"📋 Found {len(all_case_urls)} unique case URLs")
        
        # Scrape each case
        for i, url in enumerate(all_case_urls):
            case_data = await scrape_case_page(session, url)
            
            if case_data:
                normalized = normalize_charley_case(case_data)
                
                # Download image
                if download_images and normalized['victim'].get('photo_url'):
                    img_url = normalized['victim']['photo_url']
                    filename = f"charley_{normalized['case_id']}.jpg"
                    save_path = images_dir / "charley" / filename
                    
                    if await download_image(session, img_url, save_path):
                        normalized['victim']['photo_local_path'] = str(save_path)
                
                all_cases.append(normalized)
            
            if i > 0 and i % 25 == 0:
                print(f"   Scraped {i}/{len(all_case_urls)} cases...")
            
            await asyncio.sleep(0.3)  # Rate limiting
    
    print(f"✅ Scraped {len(all_cases)} Charley Project cases")
    return all_cases


if __name__ == "__main__":
    import json
    from data_pipeline.config import IMAGES_DIR
    
    cases = asyncio.run(scrape_charley_project(IMAGES_DIR, max_cases=10, download_images=False))
    if cases:
        print(f"\nSample case:\n{json.dumps(cases[0], indent=2, default=str)}")
