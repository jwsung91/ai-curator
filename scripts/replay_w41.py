"""One-off replay of W41 using only the original archived daily evidence."""
import hashlib
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from quality_pipeline import generate_quality_report
from weekly_builder import get_week_dates, read_week_data, _build_global_items, save_weekly_to_markdown
from weekly_main import MIN_DAILY_REPORTS


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'artifacts' / 'prompt-comparison'
REFERENCE = datetime(2026, 10, 10)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    days = read_week_data(get_week_dates(REFERENCE))
    if len(days) < MIN_DAILY_REPORTS:
        raise ValueError('Insufficient archived daily reports')
    items = _build_global_items(days)
    manifest = {
        'referenceDate': REFERENCE.date().isoformat(),
        'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'dailyInputs': {
            day['date']: hashlib.sha256((ROOT / 'reports/daily' / (day['date'] + '.json')).read_bytes()).hexdigest()
            for day in days
        },
        'itemCount': len(items),
    }
    trace = []
    try:
        result = generate_quality_report(items, 'weekly', '2026-10-10', trace_out=trace)
        save_weekly_to_markdown(result, days, REFERENCE)
        for suffix in ('.md', '.json'):
            source = ROOT / 'reports/weekly' / ('2026-W41' + suffix)
            shutil.copy2(source, OUTPUT / source.name)
        manifest['status'] = 'pass'
    except Exception as error:
        manifest.update(status='failed', errorType=type(error).__name__)
        if isinstance(error, ValueError):
            manifest['validationError'] = str(error)
        raise
    finally:
        (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        (OUTPUT / 'trace.json').write_text(json.dumps(trace, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
