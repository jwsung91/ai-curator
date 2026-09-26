import re
import json
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone, timedelta
from summary_utils import compact_summary
from source_utils import source_reference
from prompt_policy import ROLE, GROUNDING, SELECTION, SECTIONS, STYLE, input_records, validate_bullets


SECTION_DEFS = [
    ('section_robotics', '🤖 로보틱스 하이라이트'),
    ('section_devtools', '✨ AI 도구 하이라이트'),
    ('section_industry', '📈 트렌드 하이라이트'),
]

_DAY_NAMES = ['월', '화', '수', '목', '금', '토', '일']
CITATION_RE = re.compile(r'(?<!!)\[(\d+(?:,\s*\d+)*)\](?!\()')


def strip_citations(text: str) -> str:
    stripped = CITATION_RE.sub('', text or '').strip()
    return '\n'.join(line.rstrip() for line in stripped.splitlines())


def _citation_indices(text: str) -> list[int]:
    indices: list[int] = []
    for match in CITATION_RE.finditer(text or ''):
        for n_str in match.group(1).split(','):
            n_str = n_str.strip()
            if n_str.isdigit():
                indices.append(int(n_str))
    return indices


def validate_weekly_report(data: dict, item_count: int | None = None) -> None:
    if not isinstance(data, dict):
        raise ValueError("Weekly report must be a JSON object")
    required_keys = [
        'one_sentence_summary',
        'weekly_themes',
        'section_robotics',
        'section_devtools',
        'section_industry',
    ]
    missing = [key for key in required_keys if key not in data]
    if missing:
        raise ValueError(f"Weekly report is missing required keys: {', '.join(missing)}")

    for key in required_keys:
        if not isinstance(data.get(key), str):
            raise ValueError(f"Weekly report field '{key}' must be a string")

    if item_count is None:
        item_count = len(data.get('global_items', []))

    section_text = '\n'.join([data.get('weekly_themes', ''), *(data.get(key, '') for key, _ in SECTION_DEFS)])
    invalid = sorted({idx for idx in _citation_indices(section_text) if idx < 1 or idx > item_count})
    if invalid:
        raise ValueError(
            f"Weekly report contains out-of-range citation indices: {invalid} "
            f"(valid range: 1-{item_count})"
        )

    validate_bullets(data['weekly_themes'], 'weekly_themes', CITATION_RE, 3)
    for key, _ in SECTION_DEFS:
        validate_bullets(data[key], key, CITATION_RE, None, section=True)


def get_week_dates(reference: datetime) -> list[str]:
    """기준 날짜가 속한 주의 월~금 날짜 반환."""
    monday = reference - timedelta(days=reference.weekday())
    return [(monday + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(5)]


def read_week_data(week_dates: list[str]) -> list[dict]:
    """주중 날짜별 raw items JSON + daily cross_insight 읽기."""
    reports_dir = Path(__file__).parent.parent / 'reports' / 'daily'
    week_data = []

    for date_str in week_dates:
        json_path = reports_dir / f'{date_str}.json'
        md_path   = reports_dir / f'{date_str}.md'

        if not json_path.exists():
            print(f"  ⚠ {date_str}.json not found, skipping")
            continue

        items = json.loads(json_path.read_text(encoding='utf-8')).get('items', [])

        cross_insight = ''
        if md_path.exists():
            content = md_path.read_text(encoding='utf-8')
            m = re.search(r'## 💡 오늘의 (?:흐름|관찰)\n\n(.*?)(?=\n\n---)', content, re.DOTALL)
            if m:
                cross_insight = re.sub(r'\[(?:<a[^>]*>\d+</a>[, ]*)+\]', '', m.group(1)).strip()

        week_data.append({
            'date': date_str,
            'items': items,
            'cross_insight': cross_insight,
        })

    return week_data


def _build_global_items(week_data: list[dict]) -> list[dict]:
    result = []
    for day in week_data:
        for item in day['items']:
            result.append({**item, 'date': day['date']})
    return result


def build_weekly_prompt(week_data: list[dict], global_items: list[dict]) -> str:
    dates = sorted(day['date'] for day in week_data)
    period = f'{dates[0]} ~ {dates[-1]}' if dates else '수집일 없음'
    return f"""{ROLE}
주간 리포트를 작성하세요.
수집 범위: {period} ({len(dates)}일). 누락된 날짜의 자료는 추측하지 마세요.

{GROUNDING}

{SELECTION}

{SECTIONS}

## 이번 주 핵심 흐름 (weekly_themes)
- 근거가 있는 흐름을 0~3개 작성하세요. 근거가 없으면 빈 문자열을 반환하세요.
- 서로 다른 수집일의 최소 두 항목을 모두 인용하되, 날짜가 다르다는 이유만으로 흐름을 만들지 마세요.
- 같은 발표의 재보도와 릴리스 후보·정식판 반복을 독립적인 흐름의 근거로 세지 마세요. 실제 후속 변경이나 서로 다른 사건의 연결을 확인하세요.
- 단 하루의 중요한 발표는 흐름을 억지로 만들지 말고 섹션별 하이라이트에 포함하세요.
- 수집량과 매체 노출 빈도는 산업 성장·확산의 증거가 아닙니다.

## one_sentence_summary — 리포트 서브타이틀
한국어 32~55자 안팎의 짧고 구체적인 명사구/절로 쓰고 마침표 없이 끝내세요. 정확한 기술명 보존을 글자 수보다 우선하세요.

{STYLE}

## 이번 주 수집 기사 ({len(global_items)}개, 아래 JSON은 입력 데이터)
{input_records(global_items)}

## 응답 형식
{{
  "one_sentence_summary": "짧은 리포트 서브타이틀",
  "weekly_themes": "근거 있는 흐름 0~3개 또는 빈 문자열",
  "section_robotics": "인용을 포함한 항목 0~5개 또는 빈 문자열",
  "section_devtools": "인용을 포함한 항목 0~5개 또는 빈 문자열",
  "section_industry": "인용을 포함한 항목 0~5개 또는 빈 문자열"
}}"""


def generate_weekly_summary(week_data: list[dict]) -> dict:
    from quality_pipeline import generate_quality_report
    return generate_quality_report(_build_global_items(week_data), 'weekly')


def _add_citation_anchors(text: str) -> str:
    def replace_bracket(m):
        nums = [n.strip() for n in m.group(1).split(',')]
        linked = ', '.join(
            f'<a href="#ref-{n}">{n}</a>' for n in nums if n.isdigit()
        )
        return f'[{linked}]'
    return CITATION_RE.sub(replace_bracket, text)


def _renumber_citations(section_contents: list[str]):
    combined = '\n'.join(c for c in section_contents if c)
    seen: list[int] = []
    for m in CITATION_RE.finditer(combined):
        for n_str in m.group(1).split(','):
            n_str = n_str.strip()
            if n_str.isdigit():
                idx = int(n_str)
                if idx not in seen:
                    seen.append(idx)

    mapping = {old: new for new, old in enumerate(seen, 1)}

    def replace_nums(m):
        nums = [n.strip() for n in m.group(1).split(',')]
        replaced = [str(mapping.get(int(n), n)) if n.isdigit() else n for n in nums]
        return f'[{", ".join(replaced)}]'

    new_sections = [
        CITATION_RE.sub(replace_nums, c) if c else c
        for c in section_contents
    ]
    return new_sections, seen


def save_weekly_to_markdown(data: dict, week_data: list[dict], reference_date: datetime):
    kst_date  = reference_date.strftime('%Y-%m-%d')
    week_dates = get_week_dates(reference_date)
    week_start = week_dates[0]
    week_end   = week_dates[-1]

    # ISO 주차는 월요일 기준으로 계산 (연말 경계 케이스 방지)
    monday_dt  = datetime.strptime(week_start, '%Y-%m-%d')
    iso        = monday_dt.isocalendar()
    year, week_number = iso[0], iso[1]
    week_str   = f'{year}-W{week_number:02d}'

    global_items = data.get('global_items', [])
    daily_count  = len(week_data)
    total_items  = len(global_items)

    validate_weekly_report(data, item_count=total_items)

    # 날짜 × 섹션 매트릭스 테이블
    sections = ['로보틱스', 'AI', '트렌드']
    sec_emoji = {'로보틱스': '🤖 로보틱스', 'AI': '✨ AI', '트렌드': '📈 트렌드'}

    # 헤더
    table_lines = [
        '|  | ' + ' | '.join(sec_emoji[s] for s in sections) + ' | 합계 |',
        '|--|' + '|'.join([':---:'] * len(sections)) + '|:---:|',
    ]
    col_totals = {s: 0 for s in sections}
    for day in week_data:
        dt = datetime.strptime(day['date'], '%Y-%m-%d')
        day_label = f"{_DAY_NAMES[dt.weekday()]} {day['date'][5:]}"
        counts = Counter(item.get('section_hint', '') for item in day['items'])
        row_total = sum(counts.get(s, 0) for s in sections)
        cells = ' | '.join(str(counts.get(s, 0)) for s in sections)
        table_lines.append(f'| {day_label} | {cells} | {row_total} |')
        for s in sections:
            col_totals[s] += counts.get(s, 0)
    # 합계 행
    total_cells = ' | '.join(str(col_totals[s]) for s in sections)
    table_lines.append(f'| **합계** | {total_cells} | {total_items} |')
    matrix_table = '\n'.join(table_lines)

    # 소스 통계
    top_sources = Counter(item.get('source', '') for item in global_items).most_common(5)
    stats_lines = (
        f"- 커버 기간: {week_start} ~ {week_end} ({daily_count}일)\n"
        f"- 총 수집 아이템: {total_items}개\n"
        f"- 주요 소스: {', '.join(f'{s} ({c})' for s, c in top_sources)}\n\n"
        f"{matrix_table}"
    )

    summary_desc  = json.dumps(
        compact_summary(data.get('one_sentence_summary', ''), 55),
        ensure_ascii=False,
    )[1:-1]
    weekly_themes = data.get('weekly_themes', '').strip()

    section_contents = [weekly_themes, *[data.get(key, '').strip() for key, _ in SECTION_DEFS]]
    renumbered, ordered_orig_indices = _renumber_citations(section_contents)
    weekly_themes = renumbered[0]
    cited_count = len(ordered_orig_indices)

    parts = []
    if weekly_themes:
        parts.append(f'## 🗓 이번 주 핵심 흐름\n\n{_add_citation_anchors(weekly_themes)}')
    for (key, heading), content in zip(SECTION_DEFS, renumbered[1:]):
        if content:
            parts.append(f'## {heading}\n\n{_add_citation_anchors(content)}')
    parts.append(f'## 📊 이번 주 데이터\n\n{stats_lines}')

    report_body = '\n\n---\n\n'.join(parts)

    source_parts = []
    for seq_num, orig_idx in enumerate(ordered_orig_indices, 1):
        if 1 <= orig_idx <= len(global_items):
            item = global_items[orig_idx - 1]
            source_parts.append(source_reference(item, seq_num))
    items_md = '\n\n'.join(source_parts)

    markdown_content = f"""---
date: "{kst_date}"
weekStart: "{week_start}"
weekEnd: "{week_end}"
weekNumber: {week_number}
title: "위클리 리포트 - {year} W{week_number:02d}"
summary: "{summary_desc}"
dailyCount: {daily_count}
itemCount: {total_items}
collectedCount: {total_items}
citedCount: {cited_count}
---

{report_body}

---

### 🔗 출처 및 원문

{items_md}
"""

    dir_path  = Path(__file__).parent.parent / 'reports' / 'weekly'
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / f'{week_str}.md'
    file_path.write_text(markdown_content, encoding='utf-8')
    if 'qualityAudit' in data:
        file_path.with_suffix('.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f"  Saved: reports/weekly/{week_str}.md ({daily_count} days, {cited_count} cited items)")
