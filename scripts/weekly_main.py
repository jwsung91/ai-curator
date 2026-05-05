import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from weekly_builder import get_week_dates, read_week_data, generate_weekly_summary, save_weekly_to_markdown

MIN_DAILY_REPORTS = 3


def main():
    load_dotenv()
    force = '--force' in sys.argv

    kst   = timezone(timedelta(hours=9))
    today = datetime.now(kst)

    monday_dt   = today - timedelta(days=today.weekday())
    iso         = monday_dt.isocalendar()
    year, week_number = iso[0], iso[1]
    week_str    = f'{year}-W{week_number:02d}'

    report_path = Path(__file__).parent.parent / 'reports' / 'weekly' / f'{week_str}.md'
    if report_path.exists() and not force:
        print(f'⏭️  Weekly report {week_str} already exists. Use --force to regenerate.')
        return

    print(f'🚀 Starting Weekly Curation Pipeline... ({week_str})')

    week_dates = get_week_dates(today)
    print(f'📅 Week: {week_dates[0]} ~ {week_dates[-1]}')

    week_data = read_week_data(week_dates)

    if len(week_data) < MIN_DAILY_REPORTS:
        print(f'⚠️  Only {len(week_data)} daily reports found (minimum {MIN_DAILY_REPORTS}). Skipping.')
        return

    total_items = sum(len(d['items']) for d in week_data)
    print(f'📦 Loaded {len(week_data)} daily reports ({total_items} items total)')

    try:
        print('🤖 Generating weekly report...')
        data = generate_weekly_summary(week_data)

        print('📝 Saving...')
        save_weekly_to_markdown(data, week_data, today)
        print('✅ Done!')

    except Exception as e:
        print(f'❌ Failed: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
