#!/usr/bin/env python3
"""
Download all required datasets for Cold Case Crawler.

Datasets:
1. Kaggle Homicide Reports (requires kaggle CLI)
2. Murder Accountability Project (direct download)
3. Virginia Cold Case (API - no download needed)
4. Charley Project (scraping - no download needed)
"""
import os
import subprocess
import urllib.request
import zipfile
from pathlib import Path

from data_pipeline.config import RAW_DIR


def download_kaggle_homicide():
    """Download Kaggle Homicide Reports dataset."""
    print("\n📥 Downloading Kaggle Homicide Reports...")
    
    # Check if kaggle is installed
    try:
        subprocess.run(['kaggle', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("""
❌ Kaggle CLI not installed or not configured.

To set up:
1. pip install kaggle
2. Go to https://www.kaggle.com/settings → Create API Token
3. Save kaggle.json to ~/.kaggle/kaggle.json
4. chmod 600 ~/.kaggle/kaggle.json

Or download manually from:
https://www.kaggle.com/datasets/murderaccountability/homicide-reports
""")
        return False
    
    # Download dataset
    output_path = RAW_DIR / "homicide-reports.zip"
    
    try:
        subprocess.run([
            'kaggle', 'datasets', 'download',
            '-d', 'murderaccountability/homicide-reports',
            '-p', str(RAW_DIR)
        ], check=True)
        
        # Unzip
        if output_path.exists():
            print("   Extracting...")
            with zipfile.ZipFile(output_path, 'r') as zip_ref:
                zip_ref.extractall(RAW_DIR)
            output_path.unlink()  # Remove zip file
        
        # Check for the CSV
        csv_path = RAW_DIR / "database.csv"
        if csv_path.exists():
            # Rename to expected name
            csv_path.rename(RAW_DIR / "homicide.csv")
        
        print("✅ Kaggle Homicide Reports downloaded!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Download failed: {e}")
        return False


def download_murder_accountability():
    """Download Murder Accountability Project supplemental data."""
    print("\n📥 Downloading Murder Accountability Project data...")
    
    # The main data is the same as Kaggle, but MAP has additional resources
    # For now, we use Kaggle as the primary source
    
    print("   Note: Primary data covered by Kaggle download.")
    print("   For additional resources, visit: https://www.murderdata.org/p/data-docs.html")
    return True


def create_sample_data():
    """Create sample data for testing without downloads."""
    print("\n📝 Creating sample test data...")
    
    import csv
    import random
    
    sample_path = RAW_DIR / "homicide.csv"
    
    if sample_path.exists():
        print("   Sample data already exists, skipping...")
        return True
    
    # Create minimal sample dataset
    headers = [
        'Record ID', 'Agency Code', 'Agency Name', 'Agency Type', 'City', 'State',
        'Year', 'Month', 'Incident', 'Crime Type', 'Crime Solved', 'Victim Sex',
        'Victim Age', 'Victim Race', 'Victim Ethnicity', 'Perpetrator Sex',
        'Perpetrator Age', 'Perpetrator Race', 'Perpetrator Ethnicity',
        'Relationship', 'Weapon', 'Victim Count', 'Perpetrator Count',
        'Record Source'
    ]
    
    states = ['California', 'Texas', 'Florida', 'New York', 'Illinois', 'Ohio', 'Georgia']
    cities = ['Los Angeles', 'Houston', 'Miami', 'New York', 'Chicago', 'Columbus', 'Atlanta']
    weapons = ['Handgun', 'Knife', 'Blunt Object', 'Unknown', 'Rifle', 'Strangulation']
    races = ['White', 'Black', 'Hispanic', 'Asian', 'Unknown']
    relationships = ['Stranger', 'Acquaintance', 'Unknown', 'Family', 'Friend']
    
    rows = []
    for i in range(1000):
        state_idx = random.randint(0, len(states)-1)
        rows.append({
            'Record ID': i + 1,
            'Agency Code': f'AG{i:05d}',
            'Agency Name': f'{cities[state_idx]} PD',
            'Agency Type': 'Municipal Police',
            'City': cities[state_idx],
            'State': states[state_idx],
            'Year': random.randint(1990, 2014),
            'Month': random.randint(1, 12),
            'Incident': 1,
            'Crime Type': 'Murder or Manslaughter',
            'Crime Solved': random.choice(['Yes', 'No', 'No', 'No']),  # More unsolved
            'Victim Sex': random.choice(['Male', 'Female']),
            'Victim Age': random.randint(18, 70),
            'Victim Race': random.choice(races),
            'Victim Ethnicity': random.choice(['Hispanic', 'Not Hispanic', 'Unknown']),
            'Perpetrator Sex': random.choice(['Male', 'Female', 'Unknown']),
            'Perpetrator Age': random.randint(18, 50) if random.random() > 0.3 else 0,
            'Perpetrator Race': random.choice(races + ['Unknown']),
            'Perpetrator Ethnicity': random.choice(['Hispanic', 'Not Hispanic', 'Unknown']),
            'Relationship': random.choice(relationships),
            'Weapon': random.choice(weapons),
            'Victim Count': 1,
            'Perpetrator Count': random.choice([0, 1, 1, 1]),
            'Record Source': 'FBI'
        })
    
    with open(sample_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✅ Created sample data with {len(rows)} records at {sample_path}")
    return True


def main():
    print("="*60)
    print("🗂️  COLD CASE CRAWLER - DATASET DOWNLOAD")
    print("="*60)
    
    # Ensure directories exist
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    
    # Try Kaggle download
    kaggle_success = download_kaggle_homicide()
    
    # If Kaggle fails, create sample data for testing
    if not kaggle_success:
        print("\n⚠️  Kaggle download failed. Creating sample data for testing...")
        create_sample_data()
    
    # Murder Accountability (informational)
    download_murder_accountability()
    
    print("\n" + "="*60)
    print("📋 NEXT STEPS")
    print("="*60)
    print("""
1. Run the ingestion pipeline:
   python -m data_pipeline.ingest --source kaggle --limit 1000

2. Ingest Virginia Cold Cases (no download needed):
   python -m data_pipeline.ingest --source virginia

3. Scrape Charley Project:
   python -m data_pipeline.ingest --source charley --limit 100

4. Or run all at once:
   python -m data_pipeline.ingest --source all
""")


if __name__ == "__main__":
    main()
