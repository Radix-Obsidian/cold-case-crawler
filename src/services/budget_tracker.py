"""Budget tracking service for Cold Case Crawler."""

import json
import os
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel


class UsageRecord(BaseModel):
    """Record of API usage."""
    date: str
    service: str
    units: float  # characters for ElevenLabs, tokens for Claude
    cost: float
    episode_id: Optional[str] = None


class BudgetConfig(BaseModel):
    """Budget configuration."""
    monthly_limit: float = 50.0  # USD
    weekly_limit: float = 15.0
    daily_limit: float = 5.0
    
    # Cost estimates per service
    elevenlabs_per_char: float = 0.00003  # ~$0.30 per 10k chars
    claude_per_1k_tokens: float = 0.003   # Claude Sonnet pricing
    firecrawl_per_request: float = 0.001  # Minimal cost
    
    # Alerts
    alert_threshold: float = 0.8  # Alert at 80% of budget


class BudgetTracker:
    """Tracks API usage and enforces budget limits."""
    
    def __init__(self, data_file: str = "budget_data.json"):
        self.data_file = data_file
        self.config = BudgetConfig()
        self.usage_records: list[UsageRecord] = []
        self._load_data()
    
    def _load_data(self):
        """Load usage data from file."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r") as f:
                    data = json.load(f)
                    self.usage_records = [UsageRecord(**r) for r in data.get("records", [])]
                    if "config" in data:
                        self.config = BudgetConfig(**data["config"])
            except Exception:
                self.usage_records = []
    
    def _save_data(self):
        """Save usage data to file."""
        data = {
            "records": [r.model_dump() for r in self.usage_records],
            "config": self.config.model_dump(),
            "last_updated": datetime.now().isoformat(),
        }
        with open(self.data_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def set_limits(
        self,
        monthly: Optional[float] = None,
        weekly: Optional[float] = None,
        daily: Optional[float] = None,
    ):
        """Update budget limits."""
        if monthly is not None:
            self.config.monthly_limit = monthly
        if weekly is not None:
            self.config.weekly_limit = weekly
        if daily is not None:
            self.config.daily_limit = daily
        self._save_data()
    
    def record_usage(
        self,
        service: str,
        units: float,
        episode_id: Optional[str] = None,
    ):
        """Record API usage."""
        # Calculate cost based on service
        if service == "elevenlabs":
            cost = units * self.config.elevenlabs_per_char
        elif service == "claude":
            cost = (units / 1000) * self.config.claude_per_1k_tokens
        elif service == "firecrawl":
            cost = units * self.config.firecrawl_per_request
        else:
            cost = 0.0
        
        record = UsageRecord(
            date=datetime.now().isoformat(),
            service=service,
            units=units,
            cost=cost,
            episode_id=episode_id,
        )
        self.usage_records.append(record)
        self._save_data()
        
        return cost
    
    def get_usage(self, period: str = "daily") -> dict:
        """Get usage for a time period."""
        now = datetime.now()
        
        if period == "daily":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "weekly":
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "monthly":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start = datetime.min
        
        # Filter records
        period_records = [
            r for r in self.usage_records
            if datetime.fromisoformat(r.date) >= start
        ]
        
        # Aggregate by service
        by_service = {}
        total_cost = 0.0
        
        for record in period_records:
            if record.service not in by_service:
                by_service[record.service] = {"units": 0, "cost": 0}
            by_service[record.service]["units"] += record.units
            by_service[record.service]["cost"] += record.cost
            total_cost += record.cost
        
        # Get limit for period
        if period == "daily":
            limit = self.config.daily_limit
        elif period == "weekly":
            limit = self.config.weekly_limit
        else:
            limit = self.config.monthly_limit
        
        return {
            "period": period,
            "start": start.isoformat(),
            "total_cost": round(total_cost, 4),
            "limit": limit,
            "remaining": round(limit - total_cost, 4),
            "percent_used": round((total_cost / limit) * 100, 1) if limit > 0 else 0,
            "by_service": by_service,
        }
    
    def can_afford(self, estimated_cost: float, period: str = "daily") -> tuple[bool, str]:
        """Check if we can afford an operation."""
        usage = self.get_usage(period)
        
        if usage["remaining"] < estimated_cost:
            return False, f"Exceeds {period} budget. Remaining: ${usage['remaining']:.2f}"
        
        # Check all periods
        for p in ["daily", "weekly", "monthly"]:
            u = self.get_usage(p)
            if u["remaining"] < estimated_cost:
                return False, f"Exceeds {p} budget. Remaining: ${u['remaining']:.2f}"
        
        return True, "OK"
    
    def estimate_episode_cost(self, num_exchanges: int = 6) -> dict:
        """Estimate cost for generating an episode."""
        # Estimates based on typical usage
        avg_chars_per_line = 200
        num_lines = num_exchanges * 2  # Maya + Thorne per exchange
        total_chars = avg_chars_per_line * num_lines
        
        # Claude tokens (input + output)
        claude_tokens = 2000 + (num_lines * 100)  # System prompt + responses
        
        elevenlabs_cost = total_chars * self.config.elevenlabs_per_char
        claude_cost = (claude_tokens / 1000) * self.config.claude_per_1k_tokens
        firecrawl_cost = 5 * self.config.firecrawl_per_request  # ~5 requests
        
        total = elevenlabs_cost + claude_cost + firecrawl_cost
        
        return {
            "elevenlabs": {
                "chars": total_chars,
                "cost": round(elevenlabs_cost, 4),
            },
            "claude": {
                "tokens": claude_tokens,
                "cost": round(claude_cost, 4),
            },
            "firecrawl": {
                "requests": 5,
                "cost": round(firecrawl_cost, 4),
            },
            "total": round(total, 4),
        }
    
    def get_summary(self) -> str:
        """Get a human-readable budget summary."""
        daily = self.get_usage("daily")
        weekly = self.get_usage("weekly")
        monthly = self.get_usage("monthly")
        
        lines = [
            "💰 BUDGET SUMMARY",
            "=" * 40,
            f"Daily:   ${daily['total_cost']:.2f} / ${daily['limit']:.2f} ({daily['percent_used']}%)",
            f"Weekly:  ${weekly['total_cost']:.2f} / ${weekly['limit']:.2f} ({weekly['percent_used']}%)",
            f"Monthly: ${monthly['total_cost']:.2f} / ${monthly['limit']:.2f} ({monthly['percent_used']}%)",
            "",
        ]
        
        # Episode estimate
        estimate = self.estimate_episode_cost()
        lines.extend([
            f"📊 Episode Cost Estimate: ${estimate['total']:.2f}",
            f"   - ElevenLabs: ${estimate['elevenlabs']['cost']:.2f} ({estimate['elevenlabs']['chars']} chars)",
            f"   - Claude: ${estimate['claude']['cost']:.2f} ({estimate['claude']['tokens']} tokens)",
            "",
        ])
        
        # How many episodes can we afford?
        episodes_daily = int(daily["remaining"] / estimate["total"]) if estimate["total"] > 0 else 0
        episodes_weekly = int(weekly["remaining"] / estimate["total"]) if estimate["total"] > 0 else 0
        episodes_monthly = int(monthly["remaining"] / estimate["total"]) if estimate["total"] > 0 else 0
        
        lines.extend([
            "🎙️ Episodes Remaining:",
            f"   Today: {episodes_daily}",
            f"   This Week: {episodes_weekly}",
            f"   This Month: {episodes_monthly}",
        ])
        
        return "\n".join(lines)


def create_budget_tracker() -> BudgetTracker:
    """Create a BudgetTracker instance."""
    return BudgetTracker()
