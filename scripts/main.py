import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fetcher import (
    fetch_ros2_discourse, fetch_ros2_releases,
    fetch_simon_willison, fetch_tldr_ai, fetch_hackernews_devai, fetch_devai_releases,
    fetch_ieee_robotics, fetch_the_robot_report,
)
from builder import generate_summary, save_to_markdown

SOURCES = [
    ('로보틱스 실무',  fetch_ros2_discourse),
    ('로보틱스 실무',  fetch_ros2_releases),
    ('개발자 AI 도구', fetch_simon_willison),
    ('개발자 AI 도구', fetch_tldr_ai),
    ('개발자 AI 도구', fetch_hackernews_devai),
    ('개발자 AI 도구', fetch_devai_releases),
    ('업계 동향',      fetch_ieee_robotics),
    ('업계 동향',      fetch_the_robot_report),
]


def main():
    load_dotenv()
    print("🚀 Starting AI Curation Pipeline...")

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

        if not all_items:
            print("⚠️  No data collected. Exiting.")
            return

        print(f"\n📦 Total collected: {len(all_items)}")
        print("🧠 Generating report...")
        data = generate_summary(all_items)

        print("📝 Saving...")
        save_to_markdown(data)
        print("✅ Done!")

    except Exception as e:
        print(f"❌ Failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
