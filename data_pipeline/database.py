"""Database operations for cold case data."""
import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


def get_supabase_client() -> Client:
    """Get Supabase client from environment."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
    
    return create_client(url, key)


class CaseDatabase:
    """Handle all database operations for cold cases."""
    
    def __init__(self):
        self.client = get_supabase_client()
    
    def insert_case(self, case: Dict[str, Any]) -> Optional[str]:
        """Insert a single case with victim and evidence."""
        try:
            # Insert main case
            case_record = {
                'case_id': case['case_id'],
                'title': case['title'],
                'case_type': case['case_type'],
                'status': case['status'],
                'date_occurred': case.get('date_occurred'),
                'city': case.get('city'),
                'county': case.get('county'),
                'state': case.get('state'),
                'country': case.get('country', 'USA'),
                'latitude': case.get('latitude'),
                'longitude': case.get('longitude'),
                'summary': case.get('summary'),
                'raw_content': json.dumps(case.get('raw_data', {})),
                'source_dataset': case.get('source_dataset'),
                'source_url': case.get('source_url'),
            }
            
            result = self.client.table('case_files').upsert(
                case_record, 
                on_conflict='case_id'
            ).execute()
            
            if not result.data:
                return None
            
            case_file_id = result.data[0]['id']
            
            # Insert victim if present
            if case.get('victim'):
                self._insert_victim(case_file_id, case['victim'])
            
            # Insert evidence items
            if case.get('evidence'):
                for evidence in case['evidence']:
                    self._insert_evidence(case_file_id, evidence)
            
            # Insert source record
            self._insert_source(case_file_id, case)
            
            return case_file_id
            
        except Exception as e:
            print(f"   ❌ Error inserting case {case.get('case_id')}: {e}")
            return None
    
    def _insert_victim(self, case_file_id: str, victim: Dict) -> None:
        """Insert victim record."""
        try:
            victim_record = {
                'case_file_id': case_file_id,
                'name': victim.get('name'),
                'age_min': victim.get('age'),
                'age_max': victim.get('age'),
                'gender': victim.get('gender'),
                'race': victim.get('race'),
                'ethnicity': victim.get('ethnicity'),
                'height_inches': self._parse_height(victim.get('height')),
                'weight_lbs': self._parse_weight(victim.get('weight')),
                'hair_color': victim.get('hair_color'),
                'eye_color': victim.get('eye_color'),
                'distinguishing_marks': victim.get('distinguishing_marks'),
                'photo_url': victim.get('photo_url'),
                'photo_local_path': victim.get('photo_local_path'),
                'victim_type': 'victim',
            }
            
            self.client.table('case_victims').insert(victim_record).execute()
        except Exception as e:
            # Victim may already exist, ignore
            pass
    
    def _insert_evidence(self, case_file_id: str, evidence: Dict) -> None:
        """Insert evidence record."""
        try:
            evidence_record = {
                'case_file_id': case_file_id,
                'evidence_type': evidence.get('type', 'unknown'),
                'description': evidence.get('description', ''),
                'media_url': evidence.get('media_url'),
                'media_local_path': evidence.get('media_local_path'),
                'media_type': evidence.get('media_type'),
                'source': evidence.get('source'),
            }
            
            self.client.table('case_evidence').insert(evidence_record).execute()
        except Exception as e:
            pass
    
    def _insert_source(self, case_file_id: str, case: Dict) -> None:
        """Insert source tracking record."""
        try:
            source_record = {
                'case_file_id': case_file_id,
                'source_name': case.get('source_dataset', 'unknown'),
                'source_type': self._get_source_type(case.get('source_dataset', '')),
                'url': case.get('source_url'),
                'raw_json': case.get('raw_data'),
            }
            
            self.client.table('case_sources').upsert(
                source_record,
                on_conflict='case_file_id,source_name'
            ).execute()
        except Exception as e:
            pass
    
    def _parse_height(self, height_str) -> Optional[int]:
        """Parse height string to inches."""
        if not height_str:
            return None
        try:
            # Handle formats like "5'10" or "5 ft 10 in"
            import re
            match = re.search(r"(\d+)'?\s*(\d+)?", str(height_str))
            if match:
                feet = int(match.group(1))
                inches = int(match.group(2)) if match.group(2) else 0
                return feet * 12 + inches
        except:
            pass
        return None
    
    def _parse_weight(self, weight_str) -> Optional[int]:
        """Parse weight string to pounds."""
        if not weight_str:
            return None
        try:
            import re
            match = re.search(r"(\d+)", str(weight_str))
            if match:
                return int(match.group(1))
        except:
            pass
        return None
    
    def _get_source_type(self, source_dataset: str) -> str:
        """Determine source type from dataset name."""
        if 'kaggle' in source_dataset.lower():
            return 'kaggle'
        elif 'virginia' in source_dataset.lower():
            return 'api'
        elif 'charley' in source_dataset.lower():
            return 'scrape'
        return 'unknown'
    
    def bulk_insert_cases(self, cases: List[Dict[str, Any]], batch_size: int = 100) -> Dict:
        """Insert multiple cases with progress tracking."""
        total = len(cases)
        inserted = 0
        failed = 0
        
        print(f"\n📥 Inserting {total:,} cases into database...")
        
        for i, case in enumerate(cases):
            result = self.insert_case(case)
            if result:
                inserted += 1
            else:
                failed += 1
            
            if (i + 1) % batch_size == 0:
                print(f"   Progress: {i+1:,}/{total:,} ({inserted} inserted, {failed} failed)")
        
        print(f"✅ Complete: {inserted:,} inserted, {failed:,} failed")
        
        return {
            'total': total,
            'inserted': inserted,
            'failed': failed
        }
    
    def get_stats(self) -> Dict:
        """Get database statistics."""
        try:
            result = self.client.rpc('get_case_stats').execute()
            return result.data[0] if result.data else {}
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}
    
    def search_cases(self, query: str, limit: int = 20) -> List[Dict]:
        """Full-text search on case summaries."""
        try:
            result = self.client.table('case_files').select('*').text_search(
                'summary', query
            ).limit(limit).execute()
            return result.data
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    def get_cases_by_state(self, state: str, limit: int = 100) -> List[Dict]:
        """Get cases filtered by state."""
        try:
            result = self.client.table('case_files').select(
                '*, case_victims(*), case_evidence(*)'
            ).eq('state', state).limit(limit).execute()
            return result.data
        except Exception as e:
            print(f"Error: {e}")
            return []


if __name__ == "__main__":
    # Test database connection
    db = CaseDatabase()
    stats = db.get_stats()
    print(f"Database stats: {stats}")
