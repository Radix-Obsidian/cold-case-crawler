"""Calendar export service for Cold Case Crawler."""

import os
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import uuid4


def generate_ics_event(
    title: str,
    start: datetime,
    duration_minutes: int = 60,
    description: str = "",
    location: str = "",
    uid: Optional[str] = None,
    reminder_minutes: int = 30,
) -> str:
    """Generate a single ICS event."""
    if uid is None:
        uid = str(uuid4())
    
    end = start + timedelta(minutes=duration_minutes)
    now = datetime.utcnow()
    
    # Format dates for ICS (UTC)
    def fmt(dt: datetime) -> str:
        return dt.strftime("%Y%m%dT%H%M%SZ")
    
    # Escape special characters
    def escape(s: str) -> str:
        return s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")
    
    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}@coldcasecrawler",
        f"DTSTAMP:{fmt(now)}",
        f"DTSTART:{fmt(start)}",
        f"DTEND:{fmt(end)}",
        f"SUMMARY:{escape(title)}",
    ]
    
    if description:
        lines.append(f"DESCRIPTION:{escape(description)}")
    
    if location:
        lines.append(f"LOCATION:{escape(location)}")
    
    # Add reminder
    lines.extend([
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        f"DESCRIPTION:Reminder: {escape(title)}",
        f"TRIGGER:-PT{reminder_minutes}M",
        "END:VALARM",
    ])
    
    lines.append("END:VEVENT")
    
    return "\n".join(lines)


def generate_ics_calendar(events: List[dict], calendar_name: str = "Cold Case Crawler") -> str:
    """
    Generate a complete ICS calendar file.
    
    Args:
        events: List of event dicts with keys: title, start, duration_minutes, description
        calendar_name: Name of the calendar
    
    Returns:
        ICS file content as string
    """
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Cold Case Crawler//Podcast Schedule//EN",
        f"X-WR-CALNAME:{calendar_name}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    
    for event in events:
        event_ics = generate_ics_event(
            title=event.get("title", "Episode"),
            start=event.get("start"),
            duration_minutes=event.get("duration_minutes", 60),
            description=event.get("description", ""),
            uid=event.get("uid"),
            reminder_minutes=event.get("reminder_minutes", 30),
        )
        lines.append(event_ics)
    
    lines.append("END:VCALENDAR")
    
    return "\n".join(lines)


def export_schedule_to_ics(output_file: str = "cold_case_schedule.ics") -> str:
    """
    Export the current schedule to an ICS file.
    
    Returns:
        Path to the generated ICS file
    """
    from src.services.scheduler import create_scheduler
    
    scheduler = create_scheduler()
    upcoming = scheduler.get_upcoming_episodes(days=90)  # 3 months
    
    events = []
    for episode in upcoming:
        start = datetime.fromisoformat(episode.scheduled_date)
        
        # Create event
        events.append({
            "uid": episode.episode_id,
            "title": f"🎙️ Cold Case Crawler: {episode.case_query[:30]}",
            "start": start,
            "duration_minutes": 60,
            "description": f"""Episode Generation Day!

Case Topic: {episode.case_query}
Status: {episode.status}

To generate this episode, run:
python3 podcast_manager.py generate

Or let it run automatically with:
python3 podcast_manager.py run
""",
            "reminder_minutes": 60,  # 1 hour before
        })
    
    # Generate ICS content
    ics_content = generate_ics_calendar(events)
    
    # Save to file
    with open(output_file, "w") as f:
        f.write(ics_content)
    
    return output_file


def get_google_calendar_url(episode) -> str:
    """Generate a Google Calendar add event URL."""
    start = datetime.fromisoformat(episode.scheduled_date)
    end = start + timedelta(hours=1)
    
    # Format for Google Calendar
    start_str = start.strftime("%Y%m%dT%H%M%S")
    end_str = end.strftime("%Y%m%dT%H%M%S")
    
    title = f"🎙️ Cold Case Crawler: {episode.case_query[:30]}"
    details = f"Generate episode about: {episode.case_query}"
    
    from urllib.parse import quote
    
    url = (
        f"https://calendar.google.com/calendar/render?"
        f"action=TEMPLATE"
        f"&text={quote(title)}"
        f"&dates={start_str}/{end_str}"
        f"&details={quote(details)}"
    )
    
    return url
