"""Load and process Kaggle Homicide Reports dataset."""
import pandas as pd
import hashlib
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


def generate_case_id(row: pd.Series) -> str:
    """Generate unique case ID from row data."""
    key = f"{row.get('State', '')}-{row.get('City', '')}-{row.get('Year', '')}-{row.get('Month', '')}-{row.get('Victim Race', '')}-{row.get('Victim Age', '')}"
    return hashlib.md5(key.encode()).hexdigest()[:16]


def load_kaggle_homicide_csv(filepath: Path) -> pd.DataFrame:
    """Load the Kaggle homicide reports CSV."""
    print(f"📂 Loading Kaggle Homicide data from {filepath}")
    df = pd.read_csv(filepath, low_memory=False)
    print(f"   Loaded {len(df):,} records")
    return df


def filter_unsolved_cases(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to only unsolved/cold cases."""
    # Crime Solved: Yes/No
    unsolved = df[df['Crime Solved'] == 'No'].copy()
    print(f"   Filtered to {len(unsolved):,} unsolved cases")
    return unsolved


def normalize_to_schema(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Convert Kaggle data to our schema format."""
    cases = []
    
    for idx, row in df.iterrows():
        # Build date from Year/Month
        try:
            date_occurred = datetime(
                int(row.get('Year', 2000)), 
                int(row.get('Month', 1)), 
                1
            ).date()
        except:
            date_occurred = None
        
        case = {
            'case_id': generate_case_id(row),
            'title': f"Homicide - {row.get('City', 'Unknown')}, {row.get('State', 'Unknown')} ({row.get('Year', '')})",
            'case_type': 'homicide',
            'status': 'unsolved',
            'date_occurred': str(date_occurred) if date_occurred else None,
            'city': row.get('City'),
            'state': row.get('State'),
            'country': 'USA',
            'summary': build_summary(row),
            'source_dataset': 'kaggle_homicide',
            'source_url': 'https://www.kaggle.com/datasets/murderaccountability/homicide-reports',
            'raw_data': row.to_dict(),
            'victim': {
                'age': parse_age(row.get('Victim Age')),
                'gender': map_gender(row.get('Victim Sex')),
                'race': row.get('Victim Race'),
                'ethnicity': row.get('Victim Ethnicity'),
            },
            'evidence': [
                {
                    'type': 'physical',
                    'description': f"Weapon: {row.get('Weapon', 'Unknown')}"
                },
                {
                    'type': 'circumstantial', 
                    'description': f"Relationship: {row.get('Relationship', 'Unknown')}"
                }
            ] if row.get('Weapon') else []
        }
        cases.append(case)
        
        if idx > 0 and idx % 10000 == 0:
            print(f"   Processed {idx:,} cases...")
    
    print(f"✅ Normalized {len(cases):,} cases")
    return cases


def build_summary(row: pd.Series) -> str:
    """Build a narrative summary from the row data."""
    parts = []
    
    victim_desc = []
    if row.get('Victim Age'):
        victim_desc.append(f"{row['Victim Age']}-year-old")
    if row.get('Victim Race'):
        victim_desc.append(row['Victim Race'].lower())
    if row.get('Victim Sex'):
        victim_desc.append('male' if row['Victim Sex'] == 'Male' else 'female')
    
    if victim_desc:
        parts.append(f"A {' '.join(victim_desc)} victim")
    else:
        parts.append("A victim")
    
    parts.append(f"was found in {row.get('City', 'an unknown city')}, {row.get('State', '')}.")
    
    if row.get('Weapon') and row['Weapon'] != 'Unknown':
        parts.append(f"The weapon used was {row['Weapon'].lower()}.")
    
    if row.get('Relationship') and row['Relationship'] != 'Unknown':
        parts.append(f"The victim's relationship to the perpetrator: {row['Relationship']}.")
    
    parts.append("This case remains unsolved.")
    
    return ' '.join(parts)


def parse_age(age_val) -> int:
    """Parse age value, handling special cases."""
    if pd.isna(age_val):
        return None
    try:
        age = int(age_val)
        if age == 998 or age == 999:  # Unknown codes
            return None
        return age if 0 <= age <= 120 else None
    except:
        return None


def map_gender(sex_val) -> str:
    """Map sex values to standard gender."""
    if pd.isna(sex_val):
        return 'unknown'
    sex_val = str(sex_val).lower()
    if sex_val in ['male', 'm']:
        return 'male'
    elif sex_val in ['female', 'f']:
        return 'female'
    return 'unknown'


def process_kaggle_homicide(filepath: Path, limit: int = None) -> List[Dict[str, Any]]:
    """Full pipeline: load, filter, normalize."""
    df = load_kaggle_homicide_csv(filepath)
    df = filter_unsolved_cases(df)
    
    if limit:
        df = df.head(limit)
        print(f"   Limited to {limit} cases for testing")
    
    return normalize_to_schema(df)


if __name__ == "__main__":
    # Test with sample data
    from data_pipeline.config import RAW_DIR
    
    csv_path = RAW_DIR / "homicide.csv"
    if csv_path.exists():
        cases = process_kaggle_homicide(csv_path, limit=100)
        print(f"\nSample case:\n{cases[0]}")
    else:
        print(f"Download dataset first: kaggle datasets download -d murderaccountability/homicide-reports")
