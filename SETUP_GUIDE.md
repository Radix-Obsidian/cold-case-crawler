# Murder Index - Data Pipeline Setup Guide

Complete guide to set up the Kaggle API, run the schema in Supabase, and ingest the full 638K homicide dataset.

## Prerequisites

- Python 3.10+
- Supabase account (free tier works)
- Kaggle account

## Step 1: Set Up Kaggle API

### 1.1 Create Kaggle API Token

1. Go to [kaggle.com/settings](https://www.kaggle.com/settings)
2. Scroll to "API" section
3. Click **"Create New Token"**
4. This downloads `kaggle.json`

### 1.2 Install Kaggle Credentials

**macOS/Linux:**

```bash
mkdir -p ~/.kaggle
mv ~/Downloads/kaggle.json ~/.kaggle/
chmod 600 ~/.kaggle/kaggle.json
```

**Windows:**

```powershell
mkdir %USERPROFILE%\.kaggle
move %USERPROFILE%\Downloads\kaggle.json %USERPROFILE%\.kaggle\
```

### 1.3 Verify Installation

```bash
pip install kaggle
kaggle datasets list -s homicide
```

You should see the Murder Accountability Project dataset listed.

## Step 2: Download the Dataset

### Option A: Using the Download Script

```bash
python -m data_pipeline.download_datasets
```

### Option B: Manual Download via Kaggle CLI

```bash
kaggle datasets download -d murderaccountability/homicide-reports -p data/raw
unzip data/raw/homicide-reports.zip -d data/raw
mv data/raw/database.csv data/raw/homicide.csv
```

### Option C: Manual Download from Web

1. Visit [kaggle.com/datasets/murderaccountability/homicide-reports](https://www.kaggle.com/datasets/murderaccountability/homicide-reports)
2. Click "Download"
3. Extract to `data/raw/homicide.csv`

**Dataset Info:**
- ~638,000 homicide records (1980-2014)
- Source: FBI Supplementary Homicide Reports
- Fields: City, State, Year, Victim info, Weapon, Solved status

## Step 3: Set Up Supabase Database

### 3.1 Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Create a new project
3. Note your **Project URL** and **API Key** (anon/public)

### 3.2 Run the Schema SQL

1. In Supabase dashboard, go to **SQL Editor**
2. Copy the contents of `setup_cold_case_schema.sql`
3. Paste and click **Run**

Or use the Supabase CLI:

```bash
supabase db push --file setup_cold_case_schema.sql
```

**Schema creates:**
- `case_files` - Main case records
- `case_victims` - Victim information
- `case_evidence` - Evidence items
- `case_sources` - Data source tracking
- Indexes for fast queries
- Full-text search on summaries
- Row Level Security policies

### 3.3 Configure Environment Variables

Create `.env` file in project root:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# Optional: for service role access
SUPABASE_SERVICE_KEY=your-service-role-key
```

## Step 4: Run Data Ingestion

### 4.1 Install Dependencies

```bash
pip install -r requirements.txt
```

### 4.2 Ingest Kaggle Homicide Data

**Test with a small batch first:**

```bash
python -m data_pipeline.ingest --source kaggle --limit 1000
```

**Full ingestion (638K records):**

```bash
python -m data_pipeline.ingest --source kaggle
```

This will:
1. Load `data/raw/homicide.csv`
2. Filter to unsolved cases (~230K)
3. Transform to schema format
4. Bulk insert to Supabase

**Expected time:** ~30-60 minutes for full dataset

### 4.3 Ingest Additional Sources

**Virginia Cold Cases (API):**

```bash
python -m data_pipeline.ingest --source virginia --download-images
```

**Charley Project (scraping):**

```bash
python -m data_pipeline.ingest --source charley --limit 500 --download-images
```

**All sources at once:**

```bash
python -m data_pipeline.ingest --source all
```

## Step 5: Verify Data

### Check Database Stats

In Supabase SQL Editor:

```sql
SELECT * FROM get_case_stats();
```

Expected output:

```
total_cases   | ~300,000+
unsolved_cases| ~230,000+
missing_persons| varies
unidentified  | varies
states_covered| 50+
```

### Test API Endpoint

Start the backend:

```bash
uvicorn src.main:app --reload
```

Test the cases endpoint:

```bash
curl http://localhost:8000/cases?limit=10
```

## Troubleshooting

### "Dataset not found"

Ensure `data/raw/homicide.csv` exists. Run download script:

```bash
python -m data_pipeline.download_datasets
```

### "Kaggle CLI not configured"

Check `~/.kaggle/kaggle.json` exists and has correct permissions:

```bash
ls -la ~/.kaggle/kaggle.json
# Should show: -rw------- (600 permissions)
```

### "Supabase connection failed"

1. Verify `.env` file exists with correct values
2. Check project URL includes `https://`
3. Ensure API key is the anon/public key, not service role

### "Memory error during ingestion"

Process in smaller batches:

```bash
python -m data_pipeline.ingest --source kaggle --limit 50000
# Repeat with different offsets if needed
```

### "Rate limited by Supabase"

The free tier has limits. Either:
- Upgrade to Pro
- Reduce batch sizes in `data_pipeline/database.py`
- Add delays between batches

## Quick Reference

| Command | Description |
|---------|-------------|
| `python -m data_pipeline.download_datasets` | Download Kaggle dataset |
| `python -m data_pipeline.ingest --source kaggle` | Ingest homicide data |
| `python -m data_pipeline.ingest --source all` | Ingest all sources |
| `python -m data_pipeline.ingest --source kaggle --no-db` | JSON only, no DB |

## Data Sources Summary

| Source | Records | Type | Method |
|--------|---------|------|--------|
| Kaggle Homicide | 638K | Homicides 1980-2014 | CSV download |
| Virginia Cold Case | ~200 | State cold cases | API |
| Charley Project | 14K+ | Missing persons | Web scraping |
| NamUs | Varies | Unidentified/Missing | API (future) |
