"""Evaluate the quality-first pipeline with fixed regression data and a new daily case."""
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone
import subprocess

from google import genai
from google.genai import types
from compare_prompts import baseline_module
from article_fetcher import enrich_items
from quality_pipeline import generate_quality_report
import weekly_builder

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '055b7cf'


def main():
    output = ROOT / 'artifacts/prompt-comparison'
    output.mkdir(parents=True, exist_ok=True)
    # Freeze the v1 shared policy as well as its prompt-building code.
    import prompt_policy
    sys.modules['prompt_policy'] = baseline_module('prompt_policy', BASELINE)
    try:
        old_daily = baseline_module('builder', BASELINE)
        old_weekly = baseline_module('weekly_builder', BASELINE)
    finally:
        sys.modules['prompt_policy'] = prompt_policy
    cases = []
    for date in ('2026-09-25', '2026-09-24', '2026-09-10'):
        items = json.loads((ROOT / 'reports/daily' / f'{date}.json').read_text())['items']
        if date == '2026-09-10':
            items = enrich_items(items)
        cases.append((f'daily-{date}', 'daily', date, items, old_daily.build_prompt(items, date)))
    days = weekly_builder.read_week_data(weekly_builder.get_week_dates(datetime(2026, 9, 26)))
    items = weekly_builder._build_global_items(days)
    cases.append(('weekly-2026-W39', 'weekly', None, items, old_weekly.build_weekly_prompt(days, items)))
    model = os.getenv('GEMINI_MODEL_NAMES', 'gemini-flash-latest').split(',')[0].strip()
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'], http_options=types.HttpOptions(timeout=180000))
    manifest = {'baseline': BASELINE, 'candidate': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                'modelRequested': model, 'startedAt': datetime.now(timezone.utc).isoformat(), 'results': []}
    for name, kind, date, items, before_prompt in cases:
        case_dir = output / name
        case_dir.mkdir(exist_ok=True)
        (case_dir / 'input.json').write_text(json.dumps(items, ensure_ascii=False, indent=2))
        (case_dir / 'before.prompt.txt').write_text(before_prompt)
        for variant in ('before', 'after'):
            print(f'Evaluating {name} / {variant}', flush=True)
            trace = []
            row = {'case': name, 'variant': variant}
            try:
                if variant == 'before':
                    response = client.models.generate_content(model=model, contents=before_prompt,
                        config=types.GenerateContentConfig(response_mime_type='application/json', temperature=0.2))
                    result = json.loads(response.text)
                    row['modelVersion'] = response.model_version
                else:
                    result = generate_quality_report(items, kind, date, client, model, trace)
                    result = {k: v for k, v in result.items() if k not in ('items', 'global_items')}
                (case_dir / f'{variant}.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
                row['status'] = 'pass'
            except Exception as error:
                row.update(status='failed', errorType=type(error).__name__)
                # Only validation errors, never raw HTTP/auth diagnostics, are archived.
                if isinstance(error, ValueError):
                    row['validationError'] = str(error)
                print(f'FAILED {name}/{variant}: {type(error).__name__}', flush=True)
            if trace:
                (case_dir / 'after.trace.json').write_text(json.dumps(trace, ensure_ascii=False, indent=2))
            manifest['results'].append(row)
            (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    if any(r['status'] == 'failed' for r in manifest['results']):
        raise SystemExit('Some cases failed; inspect archived traces')


if __name__ == '__main__':
    main()
