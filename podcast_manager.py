#!/usr/bin/env python3
"""
Cold Case Crawler - Podcast Manager CLI

A budget-aware podcast management tool for solo creators.
Handles scheduling, budget tracking, and episode generation.
"""

import asyncio
import argparse
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from src.services.budget_tracker import create_budget_tracker
from src.services.scheduler import create_scheduler, ScheduleFrequency


def cmd_status(args):
    """Show current status."""
    budget = create_budget_tracker()
    scheduler = create_scheduler()
    
    print("\n" + "=" * 50)
    print("🎙️  COLD CASE CRAWLER - STATUS")
    print("=" * 50)
    print()
    print(budget.get_summary())
    print()
    print(scheduler.get_summary())
    print()


def cmd_budget(args):
    """Manage budget settings."""
    budget = create_budget_tracker()
    
    if args.set_monthly:
        budget.set_limits(monthly=args.set_monthly)
        print(f"✅ Monthly limit set to ${args.set_monthly:.2f}")
    
    if args.set_weekly:
        budget.set_limits(weekly=args.set_weekly)
        print(f"✅ Weekly limit set to ${args.set_weekly:.2f}")
    
    if args.set_daily:
        budget.set_limits(daily=args.set_daily)
        print(f"✅ Daily limit set to ${args.set_daily:.2f}")
    
    if not any([args.set_monthly, args.set_weekly, args.set_daily]):
        print("\n" + budget.get_summary())


def cmd_schedule(args):
    """Manage episode schedule."""
    scheduler = create_scheduler()
    budget = create_budget_tracker()
    
    if args.frequency:
        freq_map = {
            "daily": ScheduleFrequency.DAILY,
            "weekly": ScheduleFrequency.WEEKLY,
            "biweekly": ScheduleFrequency.BIWEEKLY,
            "monthly": ScheduleFrequency.MONTHLY,
        }
        scheduler.set_frequency(freq_map[args.frequency])
        print(f"✅ Frequency set to {args.frequency}")
    
    if args.day is not None:
        scheduler.set_preferred_time(day=args.day)
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        print(f"✅ Preferred day set to {days[args.day]}")
    
    if args.add_episodes:
        # Check budget first
        estimate = budget.estimate_episode_cost()
        total_cost = estimate["total"] * args.add_episodes
        
        can_afford, msg = budget.can_afford(total_cost, "monthly")
        if not can_afford:
            print(f"⚠️  Warning: {msg}")
            print(f"   Estimated cost for {args.add_episodes} episodes: ${total_cost:.2f}")
            response = input("   Continue anyway? (y/n): ")
            if response.lower() != 'y':
                return
        
        episodes = scheduler.schedule_multiple(args.add_episodes)
        print(f"✅ Scheduled {len(episodes)} episodes:")
        for ep in episodes:
            date = datetime.fromisoformat(ep.scheduled_date)
            print(f"   📅 {date.strftime('%b %d, %Y')} - {ep.case_query[:40]}...")
    
    if not any([args.frequency, args.day is not None, args.add_episodes]):
        print("\n" + scheduler.get_summary())


def cmd_generate(args):
    """Generate an episode."""
    from create_real_episode import create_real_episode, fetch_real_case
    
    budget = create_budget_tracker()
    scheduler = create_scheduler()
    
    # Check budget
    estimate = budget.estimate_episode_cost()
    can_afford, msg = budget.can_afford(estimate["total"])
    
    if not can_afford and not args.force:
        print(f"❌ Cannot generate: {msg}")
        print(f"   Estimated cost: ${estimate['total']:.2f}")
        print("   Use --force to override budget limits")
        return
    
    if not can_afford:
        print(f"⚠️  Warning: {msg}")
    
    print(f"\n💰 Estimated cost: ${estimate['total']:.2f}")
    print()
    
    # Run generation
    try:
        episode_data = asyncio.run(create_real_episode())
        
        # Record usage
        if episode_data:
            # Estimate actual usage (would be more accurate with real tracking)
            budget.record_usage("elevenlabs", estimate["elevenlabs"]["chars"])
            budget.record_usage("claude", estimate["claude"]["tokens"])
            budget.record_usage("firecrawl", estimate["firecrawl"]["requests"])
            
            print(f"\n✅ Episode generated successfully!")
            print(f"💰 Recorded cost: ${estimate['total']:.2f}")
    
    except Exception as e:
        print(f"\n❌ Generation failed: {e}")


def cmd_run_scheduled(args):
    """Run any pending scheduled episodes."""
    budget = create_budget_tracker()
    scheduler = create_scheduler()
    
    pending = scheduler.get_pending_episodes()
    
    if not pending:
        print("✅ No pending episodes to generate")
        return
    
    print(f"📋 Found {len(pending)} pending episode(s)")
    
    # Try to get case from database first
    print("\n🗃️  Browsing case database for material...")
    db_case = scheduler.get_case_from_database()
    if db_case:
        print(f"   📋 Pre-selected: {db_case.get('title')}")
    
    for episode in pending:
        print(f"\n🎙️  Processing: {episode.episode_id}")
        print(f"   Theme: {episode.case_query}")
        
        # Check budget
        estimate = budget.estimate_episode_cost()
        can_afford, msg = budget.can_afford(estimate["total"])
        
        if not can_afford:
            print(f"   ⏭️  Skipping: {msg}")
            scheduler.mark_skipped(episode.episode_id, msg)
            continue
        
        # Generate episode - now uses database cases automatically
        try:
            from create_real_episode import create_real_episode
            
            # create_real_episode now pulls from 638K case database
            episode_data = asyncio.run(create_real_episode())
            
            # Record usage
            budget.record_usage("elevenlabs", estimate["elevenlabs"]["chars"], episode.episode_id)
            budget.record_usage("claude", estimate["claude"]["tokens"], episode.episode_id)
            
            scheduler.mark_completed(episode.episode_id, estimate["total"])
            print(f"   ✅ Completed! Cost: ${estimate['total']:.2f}")
            
        except Exception as e:
            scheduler.mark_failed(episode.episode_id, str(e))
            print(f"   ❌ Failed: {e}")


def cmd_sources(args):
    """Manage case sources."""
    scheduler = create_scheduler()
    
    if args.add:
        scheduler.add_case_source(args.add)
        print(f"✅ Added source: {args.add}")
    
    print("\n📚 Case Sources (rotated for variety):")
    for i, source in enumerate(scheduler.config.case_sources):
        marker = "→" if i == scheduler.case_source_index else " "
        print(f"   {marker} {i+1}. {source}")


def cmd_calendar(args):
    """Export schedule to calendar."""
    from src.services.calendar_export import export_schedule_to_ics, get_google_calendar_url
    from src.services.scheduler import create_scheduler
    
    scheduler = create_scheduler()
    upcoming = scheduler.get_upcoming_episodes(days=90)
    
    if not upcoming:
        print("❌ No scheduled episodes to export")
        print("   Run: python3 podcast_manager.py schedule --add-episodes 4")
        return
    
    if args.google:
        # Print Google Calendar links
        print("\n📅 GOOGLE CALENDAR LINKS")
        print("=" * 50)
        print("Click each link to add to Google Calendar:\n")
        
        for episode in upcoming[:10]:
            date = datetime.fromisoformat(episode.scheduled_date)
            url = get_google_calendar_url(episode)
            print(f"📅 {date.strftime('%b %d, %Y')} - {episode.case_query[:25]}...")
            print(f"   {url}\n")
    
    else:
        # Export ICS file
        output_file = args.output or "cold_case_schedule.ics"
        export_schedule_to_ics(output_file)
        
        print(f"\n✅ Calendar exported to: {output_file}")
        print(f"   Episodes: {len(upcoming)}")
        print()
        print("📱 TO IMPORT:")
        print()
        print("   GOOGLE CALENDAR:")
        print("   1. Go to calendar.google.com")
        print("   2. Click ⚙️ Settings → Import & Export")
        print("   3. Select the .ics file and import")
        print()
        print("   APPLE CALENDAR:")
        print("   1. Double-click the .ics file, or")
        print("   2. File → Import → Select the .ics file")
        print()
        print("   OUTLOOK:")
        print("   1. File → Open & Export → Import/Export")
        print("   2. Import an iCalendar file")
        print()
        print("   Or use: python3 podcast_manager.py calendar --google")
        print("   to get direct Google Calendar links")


def cmd_membership(args):
    """Show membership setup instructions."""
    import os
    
    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    
    print("\n" + "=" * 50)
    print("💳 COLD CASE CRAWLER - MEMBERSHIP SETUP")
    print("=" * 50)
    print()
    
    if stripe_key:
        print("✅ Stripe API key configured")
    else:
        print("❌ Stripe API key not found")
        print()
        print("📋 SETUP STEPS:")
        print()
        print("   1. Create a Stripe account at https://stripe.com")
        print("   2. Go to Developers → API keys")
        print("   3. Copy your test keys (sk_test_... and pk_test_...)")
        print("   4. Add to your .env file:")
        print()
        print("      STRIPE_SECRET_KEY=sk_test_your-key")
        print("      STRIPE_PUBLISHABLE_KEY=pk_test_your-key")
        print("      STRIPE_WEBHOOK_SECRET=whsec_your-secret")
        print()
    
    print("💰 MEMBERSHIP TIERS:")
    print()
    print("   FREE LISTENER ($0/mo)")
    print("   • Public episodes")
    print("   • Basic case summaries")
    print()
    print("   CASE INSIDER ($9.99/mo or $99.99/yr)")
    print("   • Early access (48 hours)")
    print("   • Extended evidence files")
    print("   • Ad-free listening")
    print("   • Monthly bonus episodes")
    print()
    print("   FOUNDING INVESTIGATOR ($19.99/mo or $199.99/yr)")
    print("   • Vote on case selection")
    print("   • Name in credits")
    print("   • Exclusive merchandise")
    print("   • Direct Q&A with hosts")
    print()
    print("🌐 ENDPOINTS:")
    print()
    print("   GET  /membership/plans     - List available plans")
    print("   POST /membership/checkout  - Create checkout session")
    print("   POST /membership/webhook   - Stripe webhook handler")
    print("   GET  /membership/status/{email} - Check member status")
    print()
    print("📄 FILES:")
    print()
    print("   frontend/membership.html   - Membership signup page")
    print("   src/services/stripe_service.py - Stripe integration")
    print("   src/api/membership.py      - API routes")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Cold Case Crawler - Podcast Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s status                    Show current status
  %(prog)s budget --set-monthly 30   Set monthly budget to $30
  %(prog)s schedule --frequency weekly --add-episodes 4
  %(prog)s generate                  Generate an episode now
  %(prog)s run                       Run pending scheduled episodes
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show current status")
    status_parser.set_defaults(func=cmd_status)
    
    # Budget command
    budget_parser = subparsers.add_parser("budget", help="Manage budget")
    budget_parser.add_argument("--set-monthly", type=float, help="Set monthly limit (USD)")
    budget_parser.add_argument("--set-weekly", type=float, help="Set weekly limit (USD)")
    budget_parser.add_argument("--set-daily", type=float, help="Set daily limit (USD)")
    budget_parser.set_defaults(func=cmd_budget)
    
    # Schedule command
    schedule_parser = subparsers.add_parser("schedule", help="Manage schedule")
    schedule_parser.add_argument("--frequency", choices=["daily", "weekly", "biweekly", "monthly"])
    schedule_parser.add_argument("--day", type=int, choices=range(7), help="Preferred day (0=Mon, 6=Sun)")
    schedule_parser.add_argument("--add-episodes", type=int, help="Schedule N episodes")
    schedule_parser.set_defaults(func=cmd_schedule)
    
    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate an episode now")
    generate_parser.add_argument("--force", action="store_true", help="Override budget limits")
    generate_parser.set_defaults(func=cmd_generate)
    
    # Run scheduled command
    run_parser = subparsers.add_parser("run", help="Run pending scheduled episodes")
    run_parser.set_defaults(func=cmd_run_scheduled)
    
    # Sources command
    sources_parser = subparsers.add_parser("sources", help="Manage case sources")
    sources_parser.add_argument("--add", type=str, help="Add a case search query")
    sources_parser.set_defaults(func=cmd_sources)
    
    # Calendar command
    calendar_parser = subparsers.add_parser("calendar", help="Export schedule to calendar")
    calendar_parser.add_argument("--output", "-o", type=str, help="Output ICS file path")
    calendar_parser.add_argument("--google", action="store_true", help="Show Google Calendar links instead")
    calendar_parser.set_defaults(func=cmd_calendar)
    
    # Membership command
    membership_parser = subparsers.add_parser("membership", help="Membership & monetization setup")
    membership_parser.set_defaults(func=cmd_membership)
    
    args = parser.parse_args()
    
    if args.command is None:
        # Default to status
        cmd_status(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
