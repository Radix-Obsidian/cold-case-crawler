#!/bin/bash
# Cold Case Crawler - Scheduled Episode Runner
# Add to crontab for automated episode generation
#
# Example crontab entries:
#   Weekly on Monday at 9 AM:
#   0 9 * * 1 /path/to/cold-case-crawler/run_scheduled.sh
#
#   Daily at 6 AM:
#   0 6 * * * /path/to/cold-case-crawler/run_scheduled.sh

# Change to script directory
cd "$(dirname "$0")"

# Load environment
source .env 2>/dev/null || true

# Log file
LOG_FILE="logs/scheduled_$(date +%Y%m%d_%H%M%S).log"
mkdir -p logs

echo "========================================" | tee -a "$LOG_FILE"
echo "Cold Case Crawler - Scheduled Run" | tee -a "$LOG_FILE"
echo "$(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Run the scheduler
python3 podcast_manager.py run 2>&1 | tee -a "$LOG_FILE"

echo "" | tee -a "$LOG_FILE"
echo "Completed at $(date)" | tee -a "$LOG_FILE"
