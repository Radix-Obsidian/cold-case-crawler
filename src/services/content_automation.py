"""
Murder Index Content Automation Pipeline

Handles weekly automated content generation:
1. Case-of-the-week selection (from Charley Project data)
2. AI analysis generation (Thorne + Maya)
3. Social media post creation
4. Newsletter content preparation
5. Episode scheduling

Designed for 80-90% hands-off operation with $20/mo API budget.
"""

import os
import json
import random
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Paths
DATA_DIR = Path("data")
CONTENT_DIR = DATA_DIR / "weekly_content"
CHARLEY_DATA = Path("frontend/charley_cases.json")
CONTENT_DIR.mkdir(parents=True, exist_ok=True)


class WeeklyContent(BaseModel):
    """Weekly content package for Murder Index."""
    week_id: str  # e.g., "2026-W01"
    case_id: str
    case_title: str
    case_data: Dict[str, Any]
    
    # Generated content
    thorne_analysis: Optional[str] = None
    maya_analysis: Optional[str] = None
    murder_index_summary: Optional[str] = None
    key_questions: List[str] = []
    
    # Social media posts
    twitter_post: Optional[str] = None
    instagram_caption: Optional[str] = None
    facebook_post: Optional[str] = None
    
    # Newsletter
    newsletter_subject: Optional[str] = None
    newsletter_body: Optional[str] = None
    
    # Status
    status: str = "pending"  # pending, analysis_done, social_done, complete
    created_at: str = ""
    completed_at: Optional[str] = None


def get_week_id(date: datetime = None) -> str:
    """Get ISO week identifier."""
    if date is None:
        date = datetime.now()
    return date.strftime("%Y-W%W")


def load_charley_cases() -> List[Dict]:
    """Load cases from Charley Project JSON."""
    if not CHARLEY_DATA.exists():
        logger.error("Charley cases data not found")
        return []
    
    with open(CHARLEY_DATA, 'r') as f:
        data = json.load(f)
    return data.get('cases', [])


def calculate_case_score(case: Dict) -> int:
    """Score a case for feature potential (higher = better for content)."""
    score = 0
    
    # Has photo (critical for social media)
    if case.get('media') and len(case.get('media', [])) > 0:
        score += 50
    
    # Has detailed summary
    summary = case.get('summary', '')
    if len(summary) > 200:
        score += 20
    elif len(summary) > 100:
        score += 10
    
    # Has victim details
    victim = case.get('victim', {})
    if victim.get('name'):
        score += 10
    if victim.get('age'):
        score += 5
    if victim.get('distinguishing_marks'):
        score += 10
    
    # Has evidence
    evidence = case.get('evidence', [])
    score += min(len(evidence) * 5, 15)
    
    # Hasn't been featured recently (would need tracking)
    # For now, add some randomness
    score += random.randint(0, 10)
    
    return score


def select_case_of_the_week(exclude_ids: List[str] = None) -> Optional[Dict]:
    """Select the best case for this week's content."""
    cases = load_charley_cases()
    
    if not cases:
        logger.error("No cases available")
        return None
    
    exclude_ids = exclude_ids or []
    
    # Filter and score cases
    scored_cases = []
    for case in cases:
        case_id = case.get('case_id', '')
        if case_id in exclude_ids:
            continue
        score = calculate_case_score(case)
        scored_cases.append((score, case))
    
    if not scored_cases:
        logger.error("No eligible cases after filtering")
        return None
    
    # Sort by score and pick from top 10 (with some randomness)
    scored_cases.sort(key=lambda x: x[0], reverse=True)
    top_cases = scored_cases[:10]
    
    # Weighted random selection from top cases
    selected = random.choice(top_cases)[1]
    
    logger.info(f"Selected case: {selected.get('title')} (ID: {selected.get('case_id')})")
    return selected


def generate_social_posts(case: Dict, analysis: Dict) -> Dict[str, str]:
    """Generate social media posts for a case."""
    victim = case.get('victim', {})
    name = victim.get('name', 'Unknown')
    summary = case.get('summary', '')[:200]
    source_url = case.get('source_url', '')
    
    # Key question from analysis
    key_q = analysis.get('key_questions', ['What happened?'])[0] if analysis.get('key_questions') else 'What happened?'
    
    # Twitter (280 chars)
    twitter = f"""🔍 CASE OF THE WEEK: {name}

{summary[:100]}...

{key_q}

Full analysis on Murder Index 👇
#TrueCrime #ColdCase #MissingPerson #MurderIndex"""
    
    # Instagram (longer, more emotional)
    instagram = f"""🔍 CASE OF THE WEEK

{name} vanished without a trace.

{summary}

Dr. Thorne and Maya have analyzed this case. The evidence raises disturbing questions...

{key_q}

What do YOU think happened? Drop your theories in the comments 👇

Full expert analysis available on MurderIndex.com (link in bio)

#truecrime #coldcase #missingperson #unsolved #truecrimecommunity #murderindex #crimejunkie #investigation #mystery"""
    
    # Facebook (can be longer, more conversational)
    facebook = f"""🔍 MURDER INDEX - Case of the Week

This week, we're examining the disappearance of {name}.

{summary}

Our team has conducted a full analysis:
🔬 Dr. Thorne's Forensic Assessment
🧠 Maya's Psychological Profile
❓ Key Unanswered Questions

One question that haunts us: {key_q}

What's YOUR theory? Share in the comments and join the investigation at MurderIndex.com

#TrueCrime #ColdCase #MurderIndex"""
    
    return {
        'twitter_post': twitter[:280],
        'instagram_caption': instagram,
        'facebook_post': facebook
    }


def generate_newsletter(case: Dict, analysis: Dict) -> Dict[str, str]:
    """Generate newsletter content for a case."""
    victim = case.get('victim', {})
    name = victim.get('name', 'Unknown')
    summary = case.get('summary', '')
    
    subject = f"🔍 New Case: {name} - Murder Index Weekly"
    
    body = f"""
<h1>Murder Index Weekly</h1>

<h2>Case of the Week: {name}</h2>

<p>{summary}</p>

<h3>🔬 Dr. Thorne's Forensic Assessment</h3>
<p>{analysis.get('thorne_analysis', 'Analysis pending...')[:500]}...</p>

<h3>🧠 Maya's Psychological Profile</h3>
<p>{analysis.get('maya_analysis', 'Profile pending...')[:500]}...</p>

<h3>❓ Key Questions</h3>
<ul>
{''.join(f'<li>{q}</li>' for q in analysis.get('key_questions', ['What happened?']))}
</ul>

<p><strong>Read the full analysis:</strong> <a href="https://murderindex.com/cases">MurderIndex.com</a></p>

<hr>

<p style="color: #666; font-size: 12px;">
You're receiving this because you subscribed to Murder Index updates.
<a href="{{{{unsubscribe}}}}">Unsubscribe</a>
</p>
"""
    
    return {
        'newsletter_subject': subject,
        'newsletter_body': body
    }


async def run_weekly_pipeline(force_regenerate: bool = False) -> WeeklyContent:
    """
    Run the complete weekly content pipeline.
    
    1. Select case of the week
    2. Generate AI analysis
    3. Create social media posts
    4. Prepare newsletter
    """
    week_id = get_week_id()
    content_path = CONTENT_DIR / f"{week_id}.json"
    
    # Check if already generated this week
    if content_path.exists() and not force_regenerate:
        with open(content_path, 'r') as f:
            existing = json.load(f)
            if existing.get('status') == 'complete':
                logger.info(f"Week {week_id} already complete")
                return WeeklyContent(**existing)
    
    # Load previously featured cases to avoid repeats
    featured_ids = []
    for f in CONTENT_DIR.glob("*.json"):
        try:
            with open(f, 'r') as fp:
                data = json.load(fp)
                if data.get('case_id'):
                    featured_ids.append(data['case_id'])
        except:
            pass
    
    # Step 1: Select case
    logger.info("Step 1: Selecting case of the week...")
    case = select_case_of_the_week(exclude_ids=featured_ids)
    
    if not case:
        raise ValueError("No case available for selection")
    
    content = WeeklyContent(
        week_id=week_id,
        case_id=case.get('case_id', ''),
        case_title=case.get('title', 'Unknown'),
        case_data=case,
        created_at=datetime.utcnow().isoformat()
    )
    
    # Step 2: Generate AI analysis
    logger.info("Step 2: Generating AI analysis...")
    try:
        from src.services.case_analysis import generate_case_analysis
        
        analysis = await generate_case_analysis(case, force_regenerate=force_regenerate)
        
        content.thorne_analysis = analysis.thorne_analysis
        content.maya_analysis = analysis.maya_analysis
        content.murder_index_summary = analysis.murder_index_summary
        content.key_questions = analysis.key_questions
        content.status = "analysis_done"
        
    except Exception as e:
        logger.error(f"Analysis generation failed: {e}")
        content.status = "analysis_failed"
    
    # Save intermediate progress
    with open(content_path, 'w') as f:
        json.dump(content.model_dump(), f, indent=2)
    
    # Step 3: Generate social media posts
    logger.info("Step 3: Generating social media posts...")
    analysis_dict = {
        'thorne_analysis': content.thorne_analysis,
        'maya_analysis': content.maya_analysis,
        'key_questions': content.key_questions
    }
    
    social = generate_social_posts(case, analysis_dict)
    content.twitter_post = social['twitter_post']
    content.instagram_caption = social['instagram_caption']
    content.facebook_post = social['facebook_post']
    content.status = "social_done"
    
    # Step 4: Generate newsletter
    logger.info("Step 4: Generating newsletter...")
    newsletter = generate_newsletter(case, analysis_dict)
    content.newsletter_subject = newsletter['newsletter_subject']
    content.newsletter_body = newsletter['newsletter_body']
    
    # Mark complete
    content.status = "complete"
    content.completed_at = datetime.utcnow().isoformat()
    
    # Save final content
    with open(content_path, 'w') as f:
        json.dump(content.model_dump(), f, indent=2)
    
    logger.info(f"✅ Weekly content complete for {week_id}")
    return content


def get_weekly_content(week_id: str = None) -> Optional[WeeklyContent]:
    """Get generated content for a specific week."""
    if week_id is None:
        week_id = get_week_id()
    
    content_path = CONTENT_DIR / f"{week_id}.json"
    
    if not content_path.exists():
        return None
    
    with open(content_path, 'r') as f:
        data = json.load(f)
    
    return WeeklyContent(**data)


def list_generated_weeks() -> List[str]:
    """List all weeks with generated content."""
    weeks = []
    for f in sorted(CONTENT_DIR.glob("*.json")):
        weeks.append(f.stem)
    return weeks


# CLI runner
if __name__ == "__main__":
    import asyncio
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        result = asyncio.run(run_weekly_pipeline(force_regenerate=True))
    else:
        result = asyncio.run(run_weekly_pipeline())
    
    print(f"\n✅ Weekly content generated:")
    print(f"   Week: {result.week_id}")
    print(f"   Case: {result.case_title}")
    print(f"   Status: {result.status}")
    
    if result.twitter_post:
        print(f"\n📱 Twitter Post Preview:")
        print(f"   {result.twitter_post[:100]}...")
