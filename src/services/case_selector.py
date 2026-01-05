"""
Case Selector Service - Intelligent case selection from the database.

Used by the podcast agents to pick compelling cases for episodes,
just like a real human podcaster would browse their research materials.
"""
import os
import random
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


def get_supabase_client() -> Client:
    """Get Supabase client."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
    return create_client(url, key)


class CaseSelector:
    """
    Intelligent case selection for podcast episodes.
    
    Mimics how a real podcaster would browse cases:
    - Look for compelling narratives
    - Vary locations and time periods
    - Find cases with interesting evidence
    - Avoid recently covered cases
    - Consider seasonal/thematic relevance
    """
    
    def __init__(self):
        self.client = get_supabase_client()
        self._covered_cases: List[str] = []
        self._load_covered_cases()
    
    def _load_covered_cases(self) -> None:
        """Load list of previously covered case IDs."""
        try:
            # Check for a tracking file
            tracking_file = "data/covered_cases.json"
            if os.path.exists(tracking_file):
                import json
                with open(tracking_file, 'r') as f:
                    self._covered_cases = json.load(f)
        except:
            pass
    
    def _save_covered_case(self, case_id: str) -> None:
        """Mark a case as covered."""
        import json
        self._covered_cases.append(case_id)
        
        os.makedirs("data", exist_ok=True)
        with open("data/covered_cases.json", 'w') as f:
            json.dump(self._covered_cases[-500:], f)  # Keep last 500
    
    def get_random_unsolved(self, state: str = None, limit: int = 10) -> List[Dict]:
        """Get random unsolved cases, optionally filtered by state."""
        try:
            query = self.client.table('case_files').select(
                '*, case_victims(*), case_evidence(*)'
            ).eq('status', 'unsolved')
            
            if state:
                query = query.eq('state', state)
            
            # Get a larger pool and randomize
            result = query.limit(100).execute()
            
            if result.data:
                # Filter out covered cases
                available = [c for c in result.data if c['case_id'] not in self._covered_cases]
                return random.sample(available, min(limit, len(available)))
            return []
        except Exception as e:
            print(f"Error fetching cases: {e}")
            return []
    
    def get_compelling_case(self, criteria: Dict[str, Any] = None) -> Optional[Dict]:
        """
        Select a compelling case for the next episode.
        
        Criteria can include:
        - state: specific state to focus on
        - decade: e.g., "1980s", "1990s"
        - has_evidence: require evidence items
        - keyword: search term in summary
        - exclude_recent_states: avoid states covered recently
        """
        criteria = criteria or {}
        
        try:
            query = self.client.table('case_files').select(
                '*, case_victims(*), case_evidence(*)'
            ).eq('status', 'unsolved')
            
            # Apply filters
            if criteria.get('state'):
                query = query.eq('state', criteria['state'])
            
            if criteria.get('decade'):
                decade_start = int(criteria['decade'][:4])
                query = query.gte('date_occurred', f"{decade_start}-01-01")
                query = query.lt('date_occurred', f"{decade_start + 10}-01-01")
            
            if criteria.get('keyword'):
                query = query.ilike('summary', f"%{criteria['keyword']}%")
            
            # Get pool of candidates
            result = query.limit(50).execute()
            
            if not result.data:
                # Fallback: get any unsolved case
                result = self.client.table('case_files').select(
                    '*, case_victims(*), case_evidence(*)'
                ).eq('status', 'unsolved').limit(50).execute()
            
            if result.data:
                # Filter out covered cases
                available = [c for c in result.data if c['case_id'] not in self._covered_cases]
                
                if not available:
                    # If all cases covered, reset and start over
                    available = result.data
                
                # Score and rank cases
                scored = self._score_cases(available, criteria)
                
                # Pick from top candidates with some randomness
                top_candidates = sorted(scored, key=lambda x: x[1], reverse=True)[:10]
                if top_candidates:
                    selected = random.choice(top_candidates[:3])[0]  # Pick from top 3
                    return selected
            
            return None
            
        except Exception as e:
            print(f"Error selecting case: {e}")
            return None
    
    def _score_cases(self, cases: List[Dict], criteria: Dict) -> List[tuple]:
        """Score cases based on podcast appeal."""
        scored = []
        
        recently_used_states = self._get_recent_states()
        
        for case in cases:
            score = 0
            
            # Prefer cases with detailed summaries
            summary_len = len(case.get('summary') or '')
            if summary_len > 200:
                score += 20
            elif summary_len > 100:
                score += 10
            
            # Prefer cases with evidence
            evidence_count = len(case.get('case_evidence') or [])
            score += evidence_count * 5
            
            # Prefer cases with victim info
            if case.get('case_victims'):
                score += 10
            
            # Variety bonus: avoid recently used states
            if case.get('state') not in recently_used_states:
                score += 15
            
            # Slight preference for older cases (more mysterious)
            if case.get('date_occurred'):
                try:
                    date = datetime.fromisoformat(case['date_occurred'])
                    years_old = (datetime.now() - date).days / 365
                    if years_old > 30:
                        score += 10
                    elif years_old > 20:
                        score += 5
                except:
                    pass
            
            # Random factor for variety
            score += random.randint(0, 10)
            
            scored.append((case, score))
        
        return scored
    
    def _get_recent_states(self) -> List[str]:
        """Get states from recently covered cases."""
        # Look at last 10 covered cases
        recent_case_ids = self._covered_cases[-10:]
        states = []
        
        for case_id in recent_case_ids:
            try:
                result = self.client.table('case_files').select('state').eq(
                    'case_id', case_id
                ).single().execute()
                if result.data:
                    states.append(result.data['state'])
            except:
                pass
        
        return states
    
    def mark_as_covered(self, case_id: str) -> None:
        """Mark a case as covered for an episode."""
        self._save_covered_case(case_id)
    
    def get_case_for_episode(self, theme: str = None) -> Optional[Dict]:
        """
        Main method: Get the best case for the next episode.
        
        This is what the scheduled job calls to pick a case.
        """
        criteria = {}
        
        # Apply theme-based criteria
        if theme:
            theme_lower = theme.lower()
            if any(state in theme_lower for state in ['california', 'texas', 'florida', 'new york']):
                # State-specific theme
                for state in ['California', 'Texas', 'Florida', 'New York']:
                    if state.lower() in theme_lower:
                        criteria['state'] = state
                        break
            elif '1980' in theme_lower or 'eighties' in theme_lower:
                criteria['decade'] = '1980s'
            elif '1990' in theme_lower or 'nineties' in theme_lower:
                criteria['decade'] = '1990s'
            elif any(word in theme_lower for word in ['gun', 'shooting', 'firearm']):
                criteria['keyword'] = 'handgun'
            elif any(word in theme_lower for word in ['knife', 'stabbing']):
                criteria['keyword'] = 'knife'
        
        case = self.get_compelling_case(criteria)
        
        if case:
            print(f"📋 Selected case: {case.get('title')}")
            print(f"   Location: {case.get('city')}, {case.get('state')}")
            print(f"   Date: {case.get('date_occurred')}")
            self.mark_as_covered(case['case_id'])
        
        return case
    
    def get_stats(self) -> Dict:
        """Get database statistics for the case browser."""
        try:
            result = self.client.rpc('get_case_stats').execute()
            return result.data[0] if result.data else {}
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}
    
    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """Search cases by keyword."""
        try:
            result = self.client.table('case_files').select(
                '*, case_victims(*), case_evidence(*)'
            ).or_(
                f"title.ilike.%{query}%,summary.ilike.%{query}%,city.ilike.%{query}%,state.ilike.%{query}%"
            ).limit(limit).execute()
            return result.data or []
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    def get_by_id(self, case_id: str) -> Optional[Dict]:
        """Get a specific case by ID."""
        try:
            result = self.client.table('case_files').select(
                '*, case_victims(*), case_evidence(*)'
            ).eq('case_id', case_id).single().execute()
            return result.data
        except Exception as e:
            print(f"Error fetching case: {e}")
            return None


def create_case_selector() -> CaseSelector:
    """Factory function for case selector."""
    return CaseSelector()


if __name__ == "__main__":
    # Test case selection
    selector = create_case_selector()
    
    print("\n📊 Database Stats:")
    stats = selector.get_stats()
    print(f"   Total cases: {stats.get('total_cases', 0):,}")
    print(f"   Unsolved: {stats.get('unsolved_cases', 0):,}")
    
    print("\n🎲 Selecting a case for episode...")
    case = selector.get_case_for_episode()
    
    if case:
        print(f"\n✅ Selected: {case['title']}")
        print(f"   Summary: {case.get('summary', '')[:200]}...")
    else:
        print("❌ No cases found - run data ingestion first")
