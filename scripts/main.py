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
    fetch_hackernews_trends,
    fetch_github_cpp_trending,
    fetch_github_python_trending
)
from builder import generate_summary, save_to_markdown

def main():
    load_dotenv()
    print("🚀 Starting Robotics & AI Data Pipeline (Popularity Focus)...")

    try:
        print("📡 Fetching high-signal data from sources...")
        
        all_data = []
        
        sources = [
            ("ArXiv AI", fetch_arxiv_ai_trends),
            ("ArXiv Robotics", fetch_arxiv_robotics_trends),
            ("Weekly Robotics", fetch_weekly_robotics_trends),
            ("IEEE Spectrum", fetch_ieee_robotics_trends),
            ("ROS2 Discourse (Top)", fetch_ros2_discourse_trends),
            ("HackerNews (Top)", fetch_hackernews_trends),
            ("GitHub C++", fetch_github_cpp_trending),
            ("GitHub Python", fetch_github_python_trending),
        ]

        for name, fetch_func in sources:
            print(f"- Fetching {name}...")
            all_data.extend(fetch_func())

        if not all_data:
            print("⚠️ No data found from any source. Exiting.")
            return

        print(f"📦 Total items collected: {len(all_data)}")

        print("🧠 Generating AI summary...")
        # If this fails, it will raise an exception and go to the except block
        summary_data = generate_summary(all_data)

        print("📝 Saving report to markdown...")
        save_to_markdown(summary_data)

        print("✅ Pipeline completed successfully!")

    except Exception as e:
        print(f"❌ Pipeline failed with error: {e}")
        # Exit with error code to notify GitHub Actions
        sys.exit(1)

if __name__ == "__main__":
    main()
