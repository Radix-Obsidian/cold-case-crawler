"""Episode scheduler for Cold Case Crawler."""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel
from enum import Enum


class ScheduleFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


class ScheduledEpisode(BaseModel):
    """A scheduled episode."""
    episode_id: str
    case_query: str  # Search query for finding the case
    scheduled_date: str
    status: str = "pending"  # pending, generating, completed, failed, skipped
    generated_date: Optional[str] = None
    error: Optional[str] = None
    cost: Optional[float] = None


class ScheduleConfig(BaseModel):
    """Scheduler configuration."""
    frequency: ScheduleFrequency = ScheduleFrequency.WEEKLY
    preferred_day: int = 0  # 0=Monday, 6=Sunday
    preferred_hour: int = 9  # 9 AM
    auto_publish: bool = False
    max_retries: int = 2
    
    # Case sources to rotate through
    case_sources: List[str] = [
        "unsolved murder cold case",
        "missing person cold case",
        "unidentified victim cold case",
        "mysterious disappearance unsolved",
    ]


class EpisodeScheduler:
    """Manages scheduled episode generation."""
    
    def __init__(self, data_file: str = "schedule_data.json"):
        self.data_file = data_file
        self.config = ScheduleConfig()
        self.scheduled_episodes: List[ScheduledEpisode] = []
        self.case_source_index = 0
        self._load_data()
    
    def _load_data(self):
        """Load schedule data from file."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r") as f:
                    data = json.load(f)
                    self.scheduled_episodes = [
                        ScheduledEpisode(**e) for e in data.get("episodes", [])
                    ]
                    if "config" in data:
                        self.config = ScheduleConfig(**data["config"])
                    self.case_source_index = data.get("case_source_index", 0)
            except Exception:
                pass
    
    def _save_data(self):
        """Save schedule data to file."""
        data = {
            "episodes": [e.model_dump() for e in self.scheduled_episodes],
            "config": self.config.model_dump(),
            "case_source_index": self.case_source_index,
            "last_updated": datetime.now().isoformat(),
        }
        with open(self.data_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def set_frequency(self, frequency: ScheduleFrequency):
        """Set episode generation frequency."""
        self.config.frequency = frequency
        self._save_data()
    
    def set_preferred_time(self, day: int = 0, hour: int = 9):
        """Set preferred day and time for generation."""
        self.config.preferred_day = day
        self.config.preferred_hour = hour
        self._save_data()
    
    def add_case_source(self, query: str):
        """Add a case search query to rotate through."""
        if query not in self.config.case_sources:
            self.config.case_sources.append(query)
            self._save_data()
    
    def get_next_case_query(self) -> str:
        """Get the next case query in rotation."""
        if not self.config.case_sources:
            return "cold case unsolved"
        
        query = self.config.case_sources[self.case_source_index]
        self.case_source_index = (self.case_source_index + 1) % len(self.config.case_sources)
        self._save_data()
        return query
    
    def calculate_next_date(self, from_date: Optional[datetime] = None) -> datetime:
        """Calculate the next scheduled date based on frequency."""
        if from_date is None:
            from_date = datetime.now()
        
        if self.config.frequency == ScheduleFrequency.DAILY:
            next_date = from_date + timedelta(days=1)
        elif self.config.frequency == ScheduleFrequency.WEEKLY:
            days_ahead = self.config.preferred_day - from_date.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_date = from_date + timedelta(days=days_ahead)
        elif self.config.frequency == ScheduleFrequency.BIWEEKLY:
            days_ahead = self.config.preferred_day - from_date.weekday()
            if days_ahead <= 0:
                days_ahead += 14
            next_date = from_date + timedelta(days=days_ahead)
        else:  # MONTHLY
            if from_date.month == 12:
                next_date = from_date.replace(year=from_date.year + 1, month=1, day=1)
            else:
                next_date = from_date.replace(month=from_date.month + 1, day=1)
        
        # Set preferred hour
        next_date = next_date.replace(
            hour=self.config.preferred_hour,
            minute=0,
            second=0,
            microsecond=0
        )
        
        return next_date
    
    def schedule_next_episode(self, case_query: Optional[str] = None) -> ScheduledEpisode:
        """Schedule the next episode."""
        if case_query is None:
            case_query = self.get_next_case_query()
        
        # Find the last scheduled date
        if self.scheduled_episodes:
            last_date = max(
                datetime.fromisoformat(e.scheduled_date)
                for e in self.scheduled_episodes
            )
        else:
            last_date = datetime.now()
        
        next_date = self.calculate_next_date(last_date)
        
        episode = ScheduledEpisode(
            episode_id=f"ep-{next_date.strftime('%Y%m%d')}",
            case_query=case_query,
            scheduled_date=next_date.isoformat(),
        )
        
        self.scheduled_episodes.append(episode)
        self._save_data()
        
        return episode
    
    def schedule_multiple(self, count: int) -> List[ScheduledEpisode]:
        """Schedule multiple episodes in advance."""
        episodes = []
        for _ in range(count):
            episode = self.schedule_next_episode()
            episodes.append(episode)
        return episodes
    
    def get_pending_episodes(self) -> List[ScheduledEpisode]:
        """Get episodes that are due for generation."""
        now = datetime.now()
        return [
            e for e in self.scheduled_episodes
            if e.status == "pending" and datetime.fromisoformat(e.scheduled_date) <= now
        ]
    
    def get_upcoming_episodes(self, days: int = 30) -> List[ScheduledEpisode]:
        """Get upcoming scheduled episodes."""
        now = datetime.now()
        cutoff = now + timedelta(days=days)
        return [
            e for e in self.scheduled_episodes
            if datetime.fromisoformat(e.scheduled_date) <= cutoff
        ]
    
    def mark_completed(self, episode_id: str, cost: float = 0.0):
        """Mark an episode as completed."""
        for episode in self.scheduled_episodes:
            if episode.episode_id == episode_id:
                episode.status = "completed"
                episode.generated_date = datetime.now().isoformat()
                episode.cost = cost
                break
        self._save_data()
    
    def mark_failed(self, episode_id: str, error: str):
        """Mark an episode as failed."""
        for episode in self.scheduled_episodes:
            if episode.episode_id == episode_id:
                episode.status = "failed"
                episode.error = error
                break
        self._save_data()
    
    def mark_skipped(self, episode_id: str, reason: str):
        """Mark an episode as skipped (e.g., budget exceeded)."""
        for episode in self.scheduled_episodes:
            if episode.episode_id == episode_id:
                episode.status = "skipped"
                episode.error = reason
                break
        self._save_data()
    
    def get_summary(self) -> str:
        """Get a human-readable schedule summary."""
        pending = [e for e in self.scheduled_episodes if e.status == "pending"]
        completed = [e for e in self.scheduled_episodes if e.status == "completed"]
        failed = [e for e in self.scheduled_episodes if e.status == "failed"]
        
        lines = [
            "📅 SCHEDULE SUMMARY",
            "=" * 40,
            f"Frequency: {self.config.frequency.value}",
            f"Preferred Day: {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][self.config.preferred_day]}",
            f"Preferred Time: {self.config.preferred_hour}:00",
            "",
            f"📊 Episodes:",
            f"   Pending: {len(pending)}",
            f"   Completed: {len(completed)}",
            f"   Failed: {len(failed)}",
            "",
        ]
        
        # Upcoming episodes
        upcoming = self.get_upcoming_episodes(14)
        if upcoming:
            lines.append("📆 Upcoming (next 2 weeks):")
            for ep in upcoming[:5]:
                date = datetime.fromisoformat(ep.scheduled_date)
                status_icon = "⏳" if ep.status == "pending" else "✅" if ep.status == "completed" else "❌"
                lines.append(f"   {status_icon} {date.strftime('%b %d')} - {ep.case_query[:30]}...")
        
        return "\n".join(lines)


def create_scheduler() -> EpisodeScheduler:
    """Create an EpisodeScheduler instance."""
    return EpisodeScheduler()
