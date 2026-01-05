#!/usr/bin/env python3
"""
Demo script showing what the Cold Case Crawler would generate.
This creates a realistic debate script between Maya and Dr. Thorne.
"""

from src.models.script import DialogueLine, PodcastScript

# Create a realistic debate script about a Minnesota cold case
dialogue_lines = [
    DialogueLine(
        speaker="maya_vance",
        text="Welcome back to Cold Case Crawler. I'm Maya Vance, and today we're diving into a case that's haunted Minnesota investigators for decades.",
        emotion_tag="excited"
    ),
    DialogueLine(
        speaker="dr_aris_thorne",
        text="And I'm Dr. Aris Thorne. The case Maya's referring to involves a disappearance with virtually no physical evidence - just witness testimony and circumstantial connections.",
        emotion_tag="neutral"
    ),
    DialogueLine(
        speaker="maya_vance",
        text="But here's what's fascinating - the witness accounts don't just contradict each other, they create an impossible timeline. Someone saw our victim at 3 PM, another at 5 PM, but the last confirmed sighting was actually at 2:30.",
        emotion_tag="whispers"
    ),
    DialogueLine(
        speaker="dr_aris_thorne",
        text="That's precisely the problem with this case. Without corroborating evidence, we're left with unreliable human memory. Eyewitness testimony is notoriously unreliable, especially after decades.",
        emotion_tag="scoffs"
    ),
    DialogueLine(
        speaker="maya_vance",
        text="Okay, but what about the pattern? This isn't the only disappearance in that area during that time period. Three people, all within a five-mile radius, all within six months.",
        emotion_tag="interrupting"
    ),
    DialogueLine(
        speaker="dr_aris_thorne",
        text="Correlation isn't causation, Maya. Rural Minnesota in the 1980s - people moved away, changed their lives, started over. Not every missing person is a victim of foul play.",
        emotion_tag="clears_throat"
    ),
    DialogueLine(
        speaker="maya_vance",
        text="But the families never heard from them again. No phone calls, no letters, no social media presence years later. That's not starting over - that's vanishing.",
        emotion_tag="gasps"
    ),
    DialogueLine(
        speaker="dr_aris_thorne",
        text="I'll grant you that's unusual. But without physical evidence, without a crime scene, we're speculating. The data simply doesn't support a serial killer theory.",
        emotion_tag="dramatic_pause"
    ),
    DialogueLine(
        speaker="maya_vance",
        text="Sometimes the absence of evidence IS the evidence, Dr. Thorne. Someone was very, very good at making people disappear without a trace.",
        emotion_tag="whispers"
    ),
    DialogueLine(
        speaker="dr_aris_thorne",
        text="And that's exactly the kind of thinking that leads investigations astray. We follow the evidence, not the narrative. Until we have concrete proof, this remains an unsolved missing persons case.",
        emotion_tag="sighs"
    )
]

script = PodcastScript(
    script_id="demo-script-001",
    case_id="8a3eec51-f8e5-9057-f88e-3a64eb40af85",
    episode_title="The Minnesota Vanishings: When People Just Disappear",
    chapters=dialogue_lines,
    social_hooks=[
        "Three people vanished within six months",
        "The timeline doesn't add up",
        "Someone was very good at making people disappear",
        "The absence of evidence IS the evidence"
    ]
)

print("🎙️  COLD CASE CRAWLER - DEMO EPISODE")
print("=" * 50)
print(f"Episode: {script.episode_title}")
print(f"Script ID: {script.script_id}")
print(f"Dialogue Lines: {len(script.chapters)}")
print(f"Social Hooks: {len(script.social_hooks)}")
print("\n📝 FORMATTED FOR ELEVENLABS AUDIO:")
print("-" * 50)

for i, line in enumerate(script.chapters, 1):
    speaker_name = "Maya Vance" if line.speaker == "maya_vance" else "Dr. Aris Thorne"
    formatted_text = line.to_elevenlabs_format()
    print(f"\n{i}. {speaker_name}:")
    print(f"   {formatted_text}")

print(f"\n🎯 SOCIAL MEDIA HOOKS:")
print("-" * 30)
for i, hook in enumerate(script.social_hooks, 1):
    print(f"{i}. \"{hook}\"")

print(f"\n✅ This script is ready for ElevenLabs voice synthesis!")
print("Each emotion tag ([excited], [whispers], etc.) will create natural, emotional speech.")