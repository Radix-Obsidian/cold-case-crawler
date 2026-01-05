#!/usr/bin/env python3
"""
Main data ingestion script for Cold Case Crawler.

Usage:
    python -m data_pipeline.ingest --source kaggle --limit 1000
    python -m data_pipeline.ingest --source virginia --download-images
    python -m data_pipeline.ingest --source charley --limit 500
    python -m data_pipeline.ingest --source all
"""
import argparse
import asyncio
import json
from pathlib import Path
from datetime import datetime

from data_pipeline.config import RAW_DIR, PROCESSED_DIR, IMAGES_DIR
from data_pipeline.database import CaseDatabase


def ingest_kaggle(limit: int = None, save_to_db: bool = True) -> dict:
    """Ingest Kaggle Homicide Reports dataset."""
    from data_pipeline.loaders.kaggle_loader import process_kaggle_homicide
    
    csv_path = RAW_DIR / "homicide.csv"
    
    if not csv_path.exists():
        print(f"""
❌ Kaggle dataset not found at {csv_path}

To download, run:
    pip install kaggle
    kaggle datasets download -d murderaccountability/homicide-reports -p {RAW_DIR}
    unzip {RAW_DIR}/homicide-reports.zip -d {RAW_DIR}

Or download manually from:
    https://www.kaggle.com/datasets/murderaccountability/homicide-reports
""")
        return {'status': 'error', 'message': 'Dataset not found'}
    
    print("\n" + "="*60)
    print("📊 KAGGLE HOMICIDE REPORTS INGESTION")
    print("="*60)
    
    cases = process_kaggle_homicide(csv_path, limit=limit)
    
    # Save processed data
    output_file = PROCESSED_DIR / f"kaggle_homicide_{datetime.now().strftime('%Y%m%d')}.json"
    with open(output_file, 'w') as f:
        json.dump(cases, f, default=str)
    print(f"💾 Saved to {output_file}")
    
    # Insert into database
    if save_to_db and cases:
        db = CaseDatabase()
        result = db.bulk_insert_cases(cases)
        return {'status': 'success', 'cases': len(cases), 'db_result': result}
    
    return {'status': 'success', 'cases': len(cases)}


async def ingest_virginia(download_images: bool = True, save_to_db: bool = True) -> dict:
    """Ingest Virginia Cold Case data."""
    from data_pipeline.scrapers.virginia_scraper import process_virginia_cases
    
    print("\n" + "="*60)
    print("🔍 VIRGINIA COLD CASE INGESTION")
    print("="*60)
    
    cases = await process_virginia_cases(IMAGES_DIR, download_images=download_images)
    
    if not cases:
        return {'status': 'error', 'message': 'No cases fetched'}
    
    # Save processed data
    output_file = PROCESSED_DIR / f"virginia_cases_{datetime.now().strftime('%Y%m%d')}.json"
    with open(output_file, 'w') as f:
        json.dump(cases, f, default=str)
    print(f"💾 Saved to {output_file}")
    
    # Insert into database
    if save_to_db:
        db = CaseDatabase()
        result = db.bulk_insert_cases(cases)
        return {'status': 'success', 'cases': len(cases), 'db_result': result}
    
    return {'status': 'success', 'cases': len(cases)}


async def ingest_charley(limit: int = 500, download_images: bool = True, save_to_db: bool = True) -> dict:
    """Ingest Charley Project data."""
    from data_pipeline.scrapers.charley_scraper import scrape_charley_project
    
    print("\n" + "="*60)
    print("🔍 CHARLEY PROJECT INGESTION")
    print("="*60)
    
    cases = await scrape_charley_project(IMAGES_DIR, max_cases=limit, download_images=download_images)
    
    if not cases:
        return {'status': 'error', 'message': 'No cases scraped'}
    
    # Save processed data
    output_file = PROCESSED_DIR / f"charley_cases_{datetime.now().strftime('%Y%m%d')}.json"
    with open(output_file, 'w') as f:
        json.dump(cases, f, default=str)
    print(f"💾 Saved to {output_file}")
    
    # Insert into database
    if save_to_db:
        db = CaseDatabase()
        result = db.bulk_insert_cases(cases)
        return {'status': 'success', 'cases': len(cases), 'db_result': result}
    
    return {'status': 'success', 'cases': len(cases)}


async def ingest_all(kaggle_limit: int = 10000, charley_limit: int = 500) -> dict:
    """Run all ingestion pipelines."""
    results = {}
    
    # Kaggle (synchronous)
    print("\n🚀 Starting full data ingestion pipeline...")
    results['kaggle'] = ingest_kaggle(limit=kaggle_limit)
    
    # Virginia
    results['virginia'] = await ingest_virginia(download_images=True)
    
    # Charley Project
    results['charley'] = await ingest_charley(limit=charley_limit, download_images=True)
    
    # Summary
    print("\n" + "="*60)
    print("📊 INGESTION SUMMARY")
    print("="*60)
    for source, result in results.items():
        status = result.get('status', 'unknown')
        cases = result.get('cases', 0)
        print(f"   {source}: {status} ({cases:,} cases)")
    
    # Get final database stats
    try:
        db = CaseDatabase()
        stats = db.get_stats()
        print(f"\n📈 Database totals:")
        print(f"   Total cases: {stats.get('total_cases', 0):,}")
        print(f"   Unsolved: {stats.get('unsolved_cases', 0):,}")
        print(f"   Missing persons: {stats.get('missing_persons', 0):,}")
        print(f"   States covered: {stats.get('states_covered', 0)}")
    except:
        pass
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Cold Case Data Ingestion Pipeline')
    parser.add_argument('--source', choices=['kaggle', 'virginia', 'charley', 'all'], 
                        required=True, help='Data source to ingest')
    parser.add_argument('--limit', type=int, default=None, 
                        help='Limit number of records to process')
    parser.add_argument('--download-images', action='store_true', default=True,
                        help='Download images (default: True)')
    parser.add_argument('--no-images', action='store_true',
                        help='Skip image downloads')
    parser.add_argument('--no-db', action='store_true',
                        help='Skip database insertion (save to JSON only)')
    
    args = parser.parse_args()
    
    download_images = not args.no_images
    save_to_db = not args.no_db
    
    if args.source == 'kaggle':
        result = ingest_kaggle(limit=args.limit, save_to_db=save_to_db)
    elif args.source == 'virginia':
        result = asyncio.run(ingest_virginia(download_images=download_images, save_to_db=save_to_db))
    elif args.source == 'charley':
        limit = args.limit or 500
        result = asyncio.run(ingest_charley(limit=limit, download_images=download_images, save_to_db=save_to_db))
    elif args.source == 'all':
        kaggle_limit = args.limit or 10000
        result = asyncio.run(ingest_all(kaggle_limit=kaggle_limit))
    
    print(f"\n✅ Ingestion complete: {result}")


if __name__ == "__main__":
    main()
