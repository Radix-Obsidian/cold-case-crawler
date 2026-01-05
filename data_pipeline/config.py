"""Data pipeline configuration."""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
IMAGES_DIR = DATA_DIR / "images"

# Ensure directories exist
for dir_path in [DATA_DIR, RAW_DIR, PROCESSED_DIR, IMAGES_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Data source URLs
KAGGLE_HOMICIDE_DATASET = "murderaccountability/homicide-reports"
MURDER_ACCOUNTABILITY_URL = "https://www.murderdata.org/p/data-docs.html"
VIRGINIA_COLD_CASE_API = "https://data.virginia.gov/resource/vqfu-csh5.json"
CHARLEY_PROJECT_BASE = "https://charleyproject.org"

# Supabase config (from env)
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
