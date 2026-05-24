import sys
import types
from datetime import datetime
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT / 'scripts'))

fake_google = sys.modules.get('google') or types.ModuleType('google')
fake_genai = types.ModuleType('google.genai')
fake_genai.Client = object
fake_genai.errors = types.SimpleNamespace(ClientError=Exception, ServerError=Exception)
fake_genai.types = types.SimpleNamespace(GenerateContentConfig=lambda **kwargs: kwargs)
fake_google.genai = fake_genai
sys.modules['google'] = fake_google
sys.modules['google.genai'] = fake_genai
sys.modules.setdefault('dotenv', types.SimpleNamespace(load_dotenv=lambda: None))
sys.modules.setdefault('feedparser', types.SimpleNamespace(parse=lambda content: types.SimpleNamespace(entries=[])))

import builder
import fetcher
import main as daily_main
from builder import save_to_markdown, validate_daily_report
from weekly_builder import (
    get_week_dates,
    strip_citations,
    validate_weekly_report,
)


def _daily_data():
    return {
        'one_sentence_summary': '핵심 요약',
        'cross_insight': '- 흐름 요약',
        'section_robotics': '- **ROS2**: 업데이트 [1]',
        'section_devtools': '',
        'section_industry': '- **시장**: 발표 [2]',
        'covered_count': 2,
        'used_indices': [1, 2],
        'items': [
            {'title': 'ROS2', 'link': 'https://example.com/ros2', 'source': 'ROS2'},
            {'title': '시장', 'link': 'https://example.com/market', 'source': 'News'},
        ],
    }


def test_save_to_markdown_uses_coverage_date_and_published_at(tmp_path, monkeypatch):
    scripts_dir = tmp_path / 'scripts'
    scripts_dir.mkdir()
    monkeypatch.setattr(builder, '__file__', str(scripts_dir / 'builder.py'))

    save_to_markdown(
        _daily_data(),
        date_str='2026-05-22',
        published_at='2026-05-23T06:00:00+09:00',
    )

    report = tmp_path / 'reports' / 'daily' / '2026-05-22.md'
    assert report.exists()
    content = report.read_text(encoding='utf-8')
    assert 'date: "2026-05-22"' in content
    assert 'publishedAt: "2026-05-23T06:00:00+09:00"' in content
    assert 'title: "데일리 리포트 - 2026-05-22"' in content


def test_validate_daily_report_rejects_out_of_range_citation():
    data = _daily_data()
    data['section_robotics'] = '- **ROS2**: 업데이트 [3]'

    with pytest.raises(ValueError, match='out-of-range citation'):
        validate_daily_report(data)


def test_daily_dry_run_does_not_write_files(tmp_path, monkeypatch, capsys):
    scripts_dir = tmp_path / 'scripts'
    scripts_dir.mkdir()
    reports_dir = tmp_path / 'reports' / 'daily'
    reports_dir.mkdir(parents=True)
    seen_path = scripts_dir / 'seen_links.json'
    seen_path.write_text('{}', encoding='utf-8')

    monkeypatch.setattr(daily_main, '__file__', str(scripts_dir / 'main.py'))
    monkeypatch.setattr(daily_main, 'SEEN_PATH', seen_path)
    monkeypatch.setattr(sys, 'argv', ['scripts/main.py', '--dry-run'])
    monkeypatch.setattr(
        daily_main,
        'SOURCES',
        [('AI', lambda: [{
            'title': 'T',
            'link': 'https://example.com/t',
            'summary': 'S',
            'source': 'Src',
        }])],
    )
    monkeypatch.setattr(daily_main, 'generate_summary', lambda items: {
        **_daily_data(),
        'section_industry': '',
        'items': items,
    })
    monkeypatch.setattr(
        daily_main,
        'save_to_markdown',
        lambda *args, **kwargs: pytest.fail('dry-run must not save markdown'),
    )
    monkeypatch.setattr(
        daily_main,
        'save_seen',
        lambda *args, **kwargs: pytest.fail('dry-run must not save seen links'),
    )

    daily_main.main()

    output = capsys.readouterr().out
    assert 'Dry-run result' in output
    assert seen_path.read_text(encoding='utf-8') == '{}'
    assert list(reports_dir.iterdir()) == []


def test_robotics_infra_releases_skip_prereleases_and_limit_results(monkeypatch):
    calls = []

    def fake_fetch_github_releases(repo, label, limit=1, max_age_days=14, skip_prerelease=False):
        calls.append({
            'repo': repo,
            'label': label,
            'limit': limit,
            'max_age_days': max_age_days,
            'skip_prerelease': skip_prerelease,
        })
        return [
            {
                'title': f'{label} release {idx}',
                'link': f'https://example.com/{repo}/{idx}',
                'summary': 'stable release',
                'source': f'GitHub ({label})',
            }
            for idx in range(2)
        ]

    monkeypatch.setattr(fetcher, 'fetch_github_releases', fake_fetch_github_releases)

    items = fetcher.fetch_robotics_infra_releases()

    assert len(calls) == 10
    assert all(call['skip_prerelease'] is True for call in calls)
    assert all(call['limit'] == 1 for call in calls)
    assert all(call['max_age_days'] == 14 for call in calls)
    assert len(items) == 6


def test_robotics_infra_source_is_registered_as_robotics():
    assert ('로보틱스', daily_main.fetch_robotics_infra_releases) in daily_main.SOURCES


def test_weekly_dates_are_monday_to_friday_for_saturday_run():
    dates = get_week_dates(datetime(2026, 5, 23, 9, 0, 0))

    assert dates == [
        '2026-05-18',
        '2026-05-19',
        '2026-05-20',
        '2026-05-21',
        '2026-05-22',
    ]


def test_weekly_theme_citations_are_stripped_and_validated():
    assert strip_citations('- 흐름 [16]\n- 다른 흐름 [2, 3]') == '- 흐름\n- 다른 흐름'

    data = {
        'one_sentence_summary': '주간 요약',
        'weekly_themes': strip_citations('- 흐름 [16]'),
        'section_robotics': '- **ROS2**: 업데이트 [1]',
        'section_devtools': '',
        'section_industry': '',
        'used_indices': [1],
        'global_items': [
            {'title': 'ROS2', 'link': 'https://example.com/ros2', 'source': 'ROS2'},
        ],
    }

    validate_weekly_report(data)


def test_validate_weekly_report_rejects_citations_in_themes():
    data = {
        'one_sentence_summary': '주간 요약',
        'weekly_themes': '- 흐름 [1]',
        'section_robotics': '- **ROS2**: 업데이트 [1]',
        'section_devtools': '',
        'section_industry': '',
        'used_indices': [1],
        'global_items': [
            {'title': 'ROS2', 'link': 'https://example.com/ros2', 'source': 'ROS2'},
        ],
    }

    with pytest.raises(ValueError, match='weekly_themes'):
        validate_weekly_report(data)
