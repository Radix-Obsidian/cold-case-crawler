#!/bin/bash
# Murder Index Cron Setup Script
#
# Sets up automated weekly content generation
# Run this once to configure the cron job
#
# The automation runs every Monday at 9 AM

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_PATH=$(which python3)
LOG_DIR="$SCRIPT_DIR/logs"

# Create logs directory
mkdir -p "$LOG_DIR"

echo "🎙️  Murder Index Cron Setup"
echo "==========================="
echo ""
echo "Script directory: $SCRIPT_DIR"
echo "Python path: $PYTHON_PATH"
echo ""

# Generate the cron command
CRON_CMD="0 9 * * 1 cd $SCRIPT_DIR && $PYTHON_PATH run_weekly_automation.py >> $LOG_DIR/automation.log 2>&1"

echo "Cron command to add:"
echo "---"
echo "$CRON_CMD"
echo "---"
echo ""

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "run_weekly_automation.py"; then
    echo "⚠️  Cron job already exists!"
    echo "Current crontab:"
    crontab -l | grep "run_weekly_automation"
    echo ""
    read -p "Replace existing job? (y/n): " replace
    if [ "$replace" != "y" ]; then
        echo "Aborted."
        exit 0
    fi
    # Remove existing job
    crontab -l | grep -v "run_weekly_automation.py" | crontab -
fi

# Add new cron job
(crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo "✅ Cron job installed!"
echo ""
echo "Schedule: Every Monday at 9:00 AM"
echo "Logs: $LOG_DIR/automation.log"
echo ""
echo "To verify, run: crontab -l"
echo "To remove, run: crontab -e (and delete the line)"
echo ""
echo "Alternative: Use GitHub Actions or Railway cron for cloud hosting"
