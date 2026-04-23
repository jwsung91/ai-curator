import os
import sys
from dotenv import load_dotenv

# Add scripts directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fetcher import (
    fetch_arxiv_ai_trends,
    fetch_arxiv_robotics_trends,
    fetch_weekly_robotics_trends,
    fetch_ieee_robotics_trends,
    fetch_ros2_discourse_trends,
    fetch_hackernews_trends
)
from builder import generate_summary, save_to_markdown

def main():
    load_dotenv()
    print("🚀 Starting Robotics & AI Data Pipeline...")

    print("📡 Fetching data from sources...")
    
    all_data = []
    
    sources = [
        ("ArXiv (AI)", fetch_arxiv_ai_trends),
        ("ArXiv (Robotics)", fetch_arxiv_robotics_trends),
        ("Weekly Robotics", fetch_weekly_robotics_trends),
        ("IEEE Spectrum", fetch_ieee_robotics_trends),
        ("ROS2 Discourse", fetch_ros2_discourse_trends),
        ("HackerNews", fetch_hackernews_trends),
    ]

    for name, fetch_func in sources:
        print(f"- Fetching {name}...")
        all_data.extend(fetch_func())

    if not all_data:
        print("⚠️ No data found from any source. Exiting.")
        return

    print(f"📦 Total items collected: {len(all_data)}")

    print("🧠 Generating AI summary...")
    summary_data = generate_summary(all_data)

    print("📝 Saving report to markdown...")
    save_to_markdown({
        "title": summary_data.get("title", "No Title"),
        "summary": summary_data.get("summary", ""),
        "itemCount": len(all_data),
        "items": all_data
    })

    print("✅ Pipeline completed successfully!")

if __name__ == "__main__":
    main()
