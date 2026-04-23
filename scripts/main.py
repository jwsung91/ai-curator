import os
import sys
from dotenv import load_dotenv

# Add scripts directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fetcher import fetch_arxiv_trends
from builder import generate_summary, save_to_markdown

def main():
    load_dotenv()
    print("🚀 Starting Data Pipeline...")

    print("📡 Fetching data from sources...")
    arxiv_data = fetch_arxiv_trends()

    if not arxiv_data:
        print("⚠️ No data found. Exiting.")
        return

    print("🧠 Generating AI summary...")
    summary_data = generate_summary(arxiv_data)

    print("📝 Saving report to markdown...")
    save_to_markdown({
        "title": summary_data.get("title", "No Title"),
        "summary": summary_data.get("summary", ""),
        "itemCount": len(arxiv_data),
        "items": arxiv_data
    })

    print("✅ Pipeline completed successfully!")

if __name__ == "__main__":
    main()
