"""Bounded, reproducible prompt comparison; never publishes reports or updates seen links."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import types as module_types
from datetime import datetime, timezone

from google import genai
from google.genai import types
from dotenv import load_dotenv
import builder
import weekly_builder

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '89354fdaad3fc08b88daa6fb2f0301281922e14e'


def baseline_module(filename, revision):
    source = subprocess.check_output(['git', 'show', f'{revision}:scripts/{filename}.py'], cwd=ROOT, text=True)
    module = module_types.ModuleType(f'baseline_{filename}')
    module.__file__ = str(ROOT / 'scripts' / f'{filename}.py')
    exec(compile(source, module.__file__, 'exec'), module.__dict__)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', default=BASELINE)
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/prompt-comparison')
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    load_dotenv()
    args.output.mkdir(parents=True, exist_ok=True)
    old_daily = baseline_module('builder', args.baseline)
    old_weekly = baseline_module('weekly_builder', args.baseline)
    cases = []
    for date in ['2026-09-25', '2026-09-24']:
        items = json.loads((ROOT / 'reports/daily' / f'{date}.json').read_text())['items']
        cases.append((f'daily-{date}', items, {
            'before': old_daily.build_prompt(items),
            'after': builder.build_prompt(items, date),
        }))
    days = weekly_builder.read_week_data(weekly_builder.get_week_dates(datetime(2026, 9, 26)))
    items = weekly_builder._build_global_items(days)
    cases.append(('weekly-2026-W39', items, {
        'before': old_weekly.build_weekly_prompt(days, items),
        'after': weekly_builder.build_weekly_prompt(days, items),
    }))
    manifest = {
        'baseline': args.baseline,
        'candidate': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'startedAt': datetime.now(timezone.utc).isoformat(),
        'modelRequested': os.getenv('GEMINI_MODEL_NAMES', 'gemini-flash-latest').split(',')[0].strip(),
        'config': {'response_mime_type': 'application/json', 'temperature': 0.2},
        'runsPerVariant': 1,
        'results': [],
    }
    for name, inputs, prompts in cases:
        case_dir = args.output / name
        case_dir.mkdir(exist_ok=True)
        (case_dir / 'input.json').write_text(json.dumps(inputs, ensure_ascii=False, indent=2))
        for variant, prompt in prompts.items():
            (case_dir / f'{variant}.prompt.txt').write_text(prompt)
    manifest_path = args.output / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    if args.prepare_only:
        print('Prepared three paired cases; no API requests made.')
        return
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise SystemExit('GEMINI_API_KEY is required')
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=180000))
    for case_index, (name, inputs, prompts) in enumerate(cases):
        # Alternate variant order to reduce systematic order effects.
        order = ['before', 'after'] if case_index % 2 == 0 else ['after', 'before']
        for variant in order:
            prompt = prompts[variant]
            result = {'case': name, 'variant': variant, 'promptSha256': hashlib.sha256(prompt.encode()).hexdigest()}
            started = time.monotonic()
            print(f'Generating {name} / {variant}', flush=True)
            for attempt in range(3):
                try:
                    response = client.models.generate_content(
                        model=manifest['modelRequested'], contents=prompt,
                        config=types.GenerateContentConfig(**manifest['config']),
                    )
                    break
                except Exception as error:
                    code = getattr(error, 'code', None)
                    if code in (429, 503) and attempt < 2:
                        time.sleep(30 * (attempt + 1))
                        continue
                    raise RuntimeError(f'Generation failed ({type(error).__name__}, status={code})') from None
            result['seconds'] = round(time.monotonic() - started, 2)
            result['modelVersion'] = response.model_version
            result['usage'] = response.usage_metadata.model_dump(mode='json') if response.usage_metadata else None
            text = response.text or ''
            (args.output / name / f'{variant}.response.txt').write_text(text)
            try:
                data = json.loads(text)
                result['jsonValid'] = True
                (args.output / name / f'{variant}.json').write_text(json.dumps(data, ensure_ascii=False, indent=2))
                is_weekly = name.startswith('weekly')
                checked = {**data, 'global_items' if is_weekly else 'items': inputs}
                validate = weekly_builder.validate_weekly_report if is_weekly else builder.validate_daily_report
                try:
                    validate(checked)
                    result['candidateValidation'] = 'pass'
                except ValueError as error:
                    result['candidateValidation'] = str(error)
            except (ValueError, TypeError) as error:
                result['jsonValid'] = False
                result['candidateValidation'] = type(error).__name__
            manifest['results'].append(result)
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
            print(f'Finished {name} / {variant}: {result["candidateValidation"]}', flush=True)
    print('Comparison complete; outputs saved without publication.', flush=True)


if __name__ == '__main__':
    main()
