import os
import re
import json
import time
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone, timedelta
from google import genai
from google.genai import errors, types


SECTION_DEFS = [
    ('section_robotics', '🤖 로보틱스 하이라이트'),
    ('section_devtools', '✨ AI 도구 하이라이트'),
    ('section_industry', '📈 트렌드 하이라이트'),
]

_DAY_NAMES = ['월', '화', '수', '목', '금', '토', '일']


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
            m = re.search(r'## 💡 오늘의 흐름\n\n(.*?)(?=\n\n---)', content, re.DOTALL)
            if m:
                cross_insight = m.group(1).strip()

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
    items_text = ''
    idx = 1
    for day in week_data:
        dt = datetime.strptime(day['date'], '%Y-%m-%d')
        day_name = _DAY_NAMES[dt.weekday()]
        items_text += f"### {day_name}요일 {day['date']} — {len(day['items'])}개\n\n"
        for item in day['items']:
            hint = item.get('section_hint', '')
            items_text += (
                f"[{idx}] [{hint}] {item['title']}\n"
                f"  {item['summary'][:300]}\n\n"
            )
            idx += 1

    daily_ctx = ''
    for day in week_data:
        if day.get('cross_insight'):
            dt = datetime.strptime(day['date'], '%Y-%m-%d')
            daily_ctx += f"- {_DAY_NAMES[dt.weekday()]}요일: {day['cross_insight']}\n"

    total = len(global_items)

    return f"""당신은 로봇 시스템에 AI를 통합하는 시니어 소프트웨어 엔지니어입니다.
이번 주(월~금) 수집된 기사 {total}개를 직접 읽고 주간 리포트를 작성하세요.

---

## 이번 주 수집 기사 ({total}개)

{items_text}
---

## 일간 핵심 관찰 (보조 컨텍스트)

{daily_ctx}
---

## 작성 지침

**weekly_themes — 이번 주 핵심 흐름**
- 5일에 걸쳐 반복되거나 심화된 cross-day 패턴만 3~5개 불릿으로 작성하세요.
- 단 하루에만 등장한 이슈는 포함하지 마세요.
- 단순 항목 재진술 금지 — 여러 날의 기사를 연결하는 흐름을 서술하세요.
- 형식: "- 문장1\\n- 문장2\\n..."

**section_robotics / section_devtools / section_industry — 섹션별 하이라이트**
- 각 섹션에서 이번 주 기준 상위 3~5개 항목만 선별하세요.
- 선별 기준 (우선순위 순):
  1. 여러 날에 걸쳐 언급되거나 후속 논의가 있는 항목
  2. 실무에 즉시 영향을 주는 릴리스·변경 (nightly/rc/dev 버전 제외)
  3. 업계 방향성을 보여주는 대형 발표·투자
- 형식: "- **항목명**: 핵심 내용 한 줄 [번호]"
- 해당 항목이 없으면 빈 문자열("")

**used_indices**: 하이라이트 본문에서 인용한 [번호]를 중복 없이 오름차순으로 나열하세요.

모든 텍스트는 한국어로 작성하세요 (항목명·패키지명·API명은 원문 유지).

---

## 응답 형식 (JSON)

{{
  "one_sentence_summary": "이번 주 가장 중요한 기술 흐름 한 문장",
  "weekly_themes": "- 흐름1\\n- 흐름2\\n...",
  "section_robotics": "마크다운 (없으면 빈 문자열)",
  "section_devtools": "마크다운 (없으면 빈 문자열)",
  "section_industry": "마크다운 (없으면 빈 문자열)",
  "used_indices": [1, 3, 7]
}}"""


def generate_weekly_summary(week_data: list[dict]) -> dict:
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError('GEMINI_API_KEY is not set.')

    global_items = _build_global_items(week_data)
    client = genai.Client(api_key=api_key)
    prompt = build_weekly_prompt(week_data, global_items)
    last_exception = None

    for model_name in ['gemini-flash-latest']:
        for attempt in range(2):
            try:
                print(f"  🤖 {model_name} (attempt {attempt + 1})")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type='application/json',
                    ),
                )
                data = json.loads(response.text)
                data['global_items'] = global_items
                return data
            except (errors.ClientError, errors.ServerError) as e:
                last_exception = e
                err_str = str(e)
                if '429' in err_str or '503' in err_str:
                    if attempt == 0:
                        print('  ⚠ Rate limited. Retrying in 30s...')
                        time.sleep(30)
                        continue
                if '404' in err_str or '400' in err_str:
                    print(f'  ⏭ {model_name} unavailable, trying next...')
                    break
                raise e
            except Exception as e:
                print(f'  ✗ {e}')
                last_exception = e
                break

    raise last_exception


def _add_citation_anchors(text: str) -> str:
    def replace_bracket(m):
        nums = [n.strip() for n in m.group(1).split(',')]
        linked = ', '.join(
            f'<a href="#ref-{n}">{n}</a>' for n in nums if n.isdigit()
        )
        return f'[{linked}]'
    return re.sub(r'(?<!!)\[(\d+(?:,\s*\d+)*)\](?!\()', replace_bracket, text)


def _renumber_citations(section_contents: list[str]):
    combined = '\n'.join(c for c in section_contents if c)
    seen: list[int] = []
    for m in re.finditer(r'(?<!!)\[(\d+(?:,\s*\d+)*)\](?!\()', combined):
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
        re.sub(r'(?<!!)\[(\d+(?:,\s*\d+)*)\](?!\()', replace_nums, c) if c else c
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

    summary_desc  = json.dumps(data.get('one_sentence_summary', ''), ensure_ascii=False)[1:-1]
    weekly_themes = data.get('weekly_themes', '').strip()

    section_contents = [data.get(key, '').strip() for key, _ in SECTION_DEFS]
    renumbered, ordered_orig_indices = _renumber_citations(section_contents)

    parts = []
    if weekly_themes:
        parts.append(f'## 🗓 이번 주 핵심 흐름\n\n{weekly_themes}')
    for (key, heading), content in zip(SECTION_DEFS, renumbered):
        if content:
            parts.append(f'## {heading}\n\n{_add_citation_anchors(content)}')
    parts.append(f'## 📊 이번 주 데이터\n\n{stats_lines}')

    report_body = '\n\n---\n\n'.join(parts)

    source_parts = []
    for seq_num, orig_idx in enumerate(ordered_orig_indices, 1):
        if 1 <= orig_idx <= len(global_items):
            item = global_items[orig_idx - 1]
            title_esc = item["title"].replace('"', '&quot;')
            source_esc = item["source"].replace('"', '&quot;')
            source_parts.append(
                f'<span id="ref-{seq_num}" data-title="{title_esc}" data-url="{item["link"]}" data-source="{source_esc}"></span>\n\n'
                f'{seq_num}. [{item["title"]}]({item["link"]}) — *{item["source"]}*'
            )
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

    print(f"  Saved: reports/weekly/{week_str}.md ({daily_count} days, {len(ordered_orig_indices)} cited items)")
