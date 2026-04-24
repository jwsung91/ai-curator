import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fetcher import (
    fetch_ros2_discourse, fetch_ros2_releases,
    fetch_openai_news, fetch_google_deepmind,
    fetch_simon_willison, fetch_changelog, fetch_hackernews_devai, fetch_devai_releases,
    fetch_ieee_robotics, fetch_the_robot_report,
)
from builder import generate_summary, save_to_markdown

SOURCES = [
    ('로보틱스 실무',  fetch_ros2_discourse),
    ('로보틱스 실무',  fetch_ros2_releases),
    ('개발자 AI 도구', fetch_openai_news),
    ('개발자 AI 도구', fetch_google_deepmind),
    ('개발자 AI 도구', fetch_simon_willison),
    ('개발자 AI 도구', fetch_changelog),
    ('개발자 AI 도구', fetch_hackernews_devai),
    ('개발자 AI 도구', fetch_devai_releases),
    ('업계 동향',      fetch_ieee_robotics),
    ('업계 동향',      fetch_the_robot_report),
]

SEEN_PATH = Path(__file__).parent / 'seen_links.json'
SEEN_WINDOW = 14  # days


def load_seen() -> dict:
    if SEEN_PATH.exists():
        return json.loads(SEEN_PATH.read_text())
    return {}


def save_seen(seen: dict, date_str: str, links: list[str]):
    seen[date_str] = links
    kept = dict(sorted(seen.items())[-SEEN_WINDOW:])
    SEEN_PATH.write_text(json.dumps(kept, indent=2, ensure_ascii=False))


def deduplicate(items: list, seen: dict) -> list:
    seen_links = {link for links in seen.values() for link in links}
    fresh = [item for item in items if item['link'] not in seen_links]
    skipped = len(items) - len(fresh)
    if skipped:
        print(f"  🔁 {skipped} already-reported items skipped")
    return fresh


def main():
    load_dotenv()
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        print("🧪 Dry-run mode: seen_links will not be updated")
    print("🚀 Starting AI Curation Pipeline...")

    kst = timezone(timedelta(hours=9))
    date_str = datetime.now(kst).strftime('%Y-%m-%d')

    try:
        all_items = []
        current_section = None
        for section, fetch_fn in SOURCES:
            if section != current_section:
                print(f"\n📡 [{section}]")
                current_section = section
            print(f"  - {fetch_fn.__name__}...")
            items = fetch_fn()
            for item in items:
                item['section_hint'] = section
            all_items.extend(items)

        print(f"\n📦 Collected: {len(all_items)}")

        seen = load_seen()
        all_items = deduplicate(all_items, seen)
        print(f"📦 After dedup: {len(all_items)}")

        if not all_items:
            print("⚠️  Nothing new today. Exiting.")
            return

        print("🧠 Generating report...")
        data = generate_summary(all_items)

        print("📝 Saving...")
        save_to_markdown(data)

        if not dry_run:
            save_seen(seen, date_str, [item['link'] for item in all_items])
        print("✅ Done!")

    except Exception as e:
        print(f"❌ Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
