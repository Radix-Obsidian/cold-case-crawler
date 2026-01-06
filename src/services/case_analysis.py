"""
Case Analysis Generation Service

Generates premium AI analysis from Dr. Thorne (forensic) and Maya Vance (psychological)
for individual cases. Uses on-demand generation with caching to minimize API costs.
"""

import os
import json
import hashlib
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Analysis cache directory
CACHE_DIR = Path("data/analysis_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class CaseAnalysis(BaseModel):
    """Complete case analysis from both hosts."""
    case_id: str
    thorne_analysis: Optional[str] = None
    maya_analysis: Optional[str] = None
    murder_index_summary: Optional[str] = None
    key_questions: list[str] = []
    generated_at: str = ""
    

# Simplified prompts for case analysis (not full podcast dialogue)
THORNE_ANALYSIS_PROMPT = """You are Dr. Aris Thorne, forensic psychologist and co-host of Murder Index podcast.

Analyze this missing person case from a FORENSIC perspective. Provide a brief, professional assessment.

CASE: {case_title}
VICTIM: {victim_name}
CIRCUMSTANCES: {circumstances}
EVIDENCE: {evidence}

Write 2-3 paragraphs covering:
1. What the available evidence tells us (or doesn't tell us)
2. Forensic red flags or patterns you notice
3. What modern forensic techniques could help solve this case

Keep it professional, evidence-focused, and avoid speculation without basis.
Sign off with your signature: "The evidence tells a story - we just have to listen."
"""

MAYA_ANALYSIS_PROMPT = """You are Maya Vance, criminal profiler and co-host of Murder Index podcast.

Analyze this missing person case from a PSYCHOLOGICAL/BEHAVIORAL perspective. Provide a brief, professional assessment.

CASE: {case_title}
VICTIM: {victim_name}
CIRCUMSTANCES: {circumstances}
VICTIM DETAILS: {victim_details}

Write 2-3 paragraphs covering:
1. Victimology - why might this person have been targeted?
2. Behavioral indicators - what does the disappearance pattern suggest?
3. Potential offender profile (if foul play suspected)

Be empathetic to the victim while providing professional insight.
Sign off with your signature: "Stay curious... and stay safe."
"""

SUMMARY_PROMPT = """Based on these expert analyses of a missing person case, create a brief Murder Index summary.

CASE: {case_title}
DR. THORNE'S FORENSIC ASSESSMENT: {thorne_analysis}
MAYA'S PSYCHOLOGICAL PROFILE: {maya_analysis}

Write:
1. A 2-sentence case summary
2. 3-5 key unanswered questions about this case

Format as JSON:
{{"summary": "...", "key_questions": ["...", "...", "..."]}}
"""


def get_cache_path(case_id: str) -> Path:
    """Get the cache file path for a case."""
    return CACHE_DIR / f"{case_id}_analysis.json"


def load_cached_analysis(case_id: str) -> Optional[CaseAnalysis]:
    """Load analysis from cache if it exists."""
    cache_path = get_cache_path(case_id)
    if cache_path.exists():
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
                return CaseAnalysis(**data)
        except Exception as e:
            logger.warning(f"Failed to load cached analysis for {case_id}: {e}")
    return None


def save_analysis_to_cache(analysis: CaseAnalysis) -> None:
    """Save analysis to cache."""
    cache_path = get_cache_path(analysis.case_id)
    try:
        with open(cache_path, 'w') as f:
            json.dump(analysis.model_dump(), f, indent=2)
        logger.info(f"Cached analysis for case {analysis.case_id}")
    except Exception as e:
        logger.error(f"Failed to cache analysis: {e}")


async def generate_case_analysis(case_data: Dict[str, Any], force_regenerate: bool = False) -> CaseAnalysis:
    """
    Generate AI analysis for a case using Claude.
    
    Args:
        case_data: Case data dictionary from the frontend
        force_regenerate: If True, regenerate even if cached
        
    Returns:
        CaseAnalysis with Thorne and Maya assessments
    """
    case_id = case_data.get('case_id', '')
    
    # Check cache first
    if not force_regenerate:
        cached = load_cached_analysis(case_id)
        if cached:
            logger.info(f"Using cached analysis for case {case_id}")
            return cached
    
    # Import here to avoid circular imports and only when needed
    try:
        import anthropic
    except ImportError:
        logger.error("anthropic package not installed")
        return CaseAnalysis(
            case_id=case_id,
            thorne_analysis="Analysis service temporarily unavailable.",
            maya_analysis="Analysis service temporarily unavailable.",
            generated_at=datetime.utcnow().isoformat()
        )
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        return CaseAnalysis(
            case_id=case_id,
            thorne_analysis="Analysis service not configured.",
            maya_analysis="Analysis service not configured.",
            generated_at=datetime.utcnow().isoformat()
        )
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Extract case details
    case_title = case_data.get('title', 'Unknown Case')
    victim = case_data.get('victim', {})
    victim_name = victim.get('name', 'Unknown')
    circumstances = case_data.get('summary', 'No details available.')
    evidence = case_data.get('evidence', [])
    evidence_str = "; ".join([f"{e.get('type', 'unknown')}: {e.get('description', '')}" for e in evidence]) if evidence else "No physical evidence documented"
    
    victim_details = f"Age: {victim.get('age', 'unknown')}, Gender: {victim.get('gender', 'unknown')}"
    if victim.get('hair_color'):
        victim_details += f", Hair: {victim.get('hair_color')}"
    if victim.get('distinguishing_marks'):
        victim_details += f", Distinguishing marks: {victim.get('distinguishing_marks')}"
    
    analysis = CaseAnalysis(
        case_id=case_id,
        generated_at=datetime.utcnow().isoformat()
    )
    
    try:
        # Generate Thorne's forensic analysis
        thorne_prompt = THORNE_ANALYSIS_PROMPT.format(
            case_title=case_title,
            victim_name=victim_name,
            circumstances=circumstances,
            evidence=evidence_str
        )
        
        thorne_response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": thorne_prompt}]
        )
        analysis.thorne_analysis = thorne_response.content[0].text
        logger.info(f"Generated Thorne analysis for {case_id}")
        
    except Exception as e:
        logger.error(f"Failed to generate Thorne analysis: {e}")
        analysis.thorne_analysis = "Forensic analysis temporarily unavailable."
    
    try:
        # Generate Maya's psychological profile
        maya_prompt = MAYA_ANALYSIS_PROMPT.format(
            case_title=case_title,
            victim_name=victim_name,
            circumstances=circumstances,
            victim_details=victim_details
        )
        
        maya_response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": maya_prompt}]
        )
        analysis.maya_analysis = maya_response.content[0].text
        logger.info(f"Generated Maya analysis for {case_id}")
        
    except Exception as e:
        logger.error(f"Failed to generate Maya analysis: {e}")
        analysis.maya_analysis = "Psychological profile temporarily unavailable."
    
    try:
        # Generate Murder Index summary with key questions
        if analysis.thorne_analysis and analysis.maya_analysis:
            summary_prompt = SUMMARY_PROMPT.format(
                case_title=case_title,
                thorne_analysis=analysis.thorne_analysis[:500],
                maya_analysis=analysis.maya_analysis[:500]
            )
            
            summary_response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                messages=[{"role": "user", "content": summary_prompt}]
            )
            
            # Parse JSON response
            summary_text = summary_response.content[0].text
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', summary_text, re.DOTALL)
            if json_match:
                summary_data = json.loads(json_match.group())
                analysis.murder_index_summary = summary_data.get('summary', '')
                analysis.key_questions = summary_data.get('key_questions', [])
                
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        analysis.murder_index_summary = "Summary generation in progress."
        analysis.key_questions = ["What happened to the victim?", "Who was the last person to see them?"]
    
    # Cache the result
    save_analysis_to_cache(analysis)
    
    return analysis


def create_case_analysis_service():
    """Factory function for the analysis service."""
    return {
        'generate': generate_case_analysis,
        'load_cached': load_cached_analysis,
    }
