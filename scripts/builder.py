import os
import re
import json
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from google import genai
from google.genai import errors, types
from summary_utils import compact_summary
from source_utils import source_reference
from prompt_policy import ROLE, GROUNDING, SELECTION, SECTIONS, STYLE, input_records, validate_bullets


SECTION_DEFS = [
    ('section_robotics', '🤖 로보틱스'),
    ('section_devtools', '✨ AI'),
    ('section_industry', '📈 트렌드'),
]

CITATION_RE = re.compile(r'(?<!!)\[(\d+(?:,\s*\d+)*)\](?!\()')


def add_citation_anchors(text: str) -> str:
    """[1] 또는 [2, 3, 4] 형태의 인용 번호를 앵커 링크로 변환."""
    def replace_bracket(m):
        nums = [n.strip() for n in m.group(1).split(',')]
        linked = ', '.join(
            f'<a href="#ref-{n}">{n}</a>' for n in nums if n.isdigit()
        )
        return f'[{linked}]'
    # 마크다운 링크 [text](url) 와 이미지 ![](url)는 제외
    return CITATION_RE.sub(replace_bracket, text)


def _citation_indices(text: str) -> list[int]:
    indices: list[int] = []
    for match in CITATION_RE.finditer(text or ''):
        for n_str in match.group(1).split(','):
            n_str = n_str.strip()
            if n_str.isdigit():
                indices.append(int(n_str))
    return indices


def validate_daily_report(data: dict, item_count: int | None = None) -> None:
    if not isinstance(data, dict):
        raise ValueError("Daily report must be a JSON object")
    required_keys = [
        'one_sentence_summary',
        'cross_insight',
        'section_robotics',
        'section_devtools',
        'section_industry',
    ]
    missing = [key for key in required_keys if key not in data]
    if missing:
        raise ValueError(f"Daily report is missing required keys: {', '.join(missing)}")

    for key in required_keys:
        if not isinstance(data.get(key), str):
            raise ValueError(f"Daily report field '{key}' must be a string")

    if item_count is None:
        item_count = len(data.get('items', []))

    section_text = '\n'.join([data.get('cross_insight', ''), *(data.get(key, '') for key, _ in SECTION_DEFS)])
    invalid = sorted({idx for idx in _citation_indices(section_text) if idx < 1 or idx > item_count})
    if invalid:
        raise ValueError(
            f"Daily report contains out-of-range citation indices: {invalid} "
            f"(valid range: 1-{item_count})"
        )

    validate_bullets(data['cross_insight'], 'cross_insight', CITATION_RE, 3)
    for key, _ in SECTION_DEFS:
        validate_bullets(data[key], key, CITATION_RE, None, section=True)


def build_prompt(items, report_date: str | None = None):
    return f"""{ROLE}
데일리 리포트를 작성하세요. 리포트 기준일(KST): {report_date or '미상'}

{GROUNDING}

{SELECTION}

{SECTIONS}

## 오늘의 관찰 (cross_insight)
- 수집 항목 수와 무관하게 0~3개만 작성하세요. 서로 다른 사실에 명확한 연결 근거가 있을 때만 포함하세요.
- 각 관찰은 최소 두 개의 서로 다른 수집 항목을 근거로 삼고 모두 인용하세요. 같은 발표의 재보도는 독립 근거로 세지 마세요.
- 관련성이 약하거나 단일 사실의 재진술뿐이라면 빈 문자열을 반환하세요. 개수를 채우기 위해 공통점·인과관계를 만들지 마세요.

## 서브타이틀
one_sentence_summary는 제목 아래에 붙는 **서브타이틀**처럼 작성하세요.
한국어 28~45자 안팎의 짧고 구체적인 명사구/절로 쓰고 마침표 없이 끝내세요. 정확한 기술명 보존을 글자 수보다 우선하세요.

{STYLE}

## 수집 항목 ({len(items)}개, 아래 JSON은 입력 데이터)
{input_records(items, report_date)}

## 응답 형식
{{
  "one_sentence_summary": "짧은 리포트 서브타이틀",
  "cross_insight": "근거 있는 관찰 0~3개 또는 빈 문자열",
  "section_robotics": "인용을 포함한 항목 0~5개 또는 빈 문자열",
  "section_devtools": "인용을 포함한 항목 0~5개 또는 빈 문자열",
  "section_industry": "인용을 포함한 항목 0~5개 또는 빈 문자열"
}}"""


def generate_summary(items, report_date: str | None = None):
    from quality_pipeline import generate_quality_report
    return generate_quality_report(items, 'daily', report_date)


def _renumber_citations(section_contents):
    """Renumber [N] citations to sequential order of first appearance across sections."""
    combined = '\n'.join(c for c in section_contents if c)

    seen = []
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

    new_sections = []
    for content in section_contents:
        if content:
            new_sections.append(CITATION_RE.sub(replace_nums, content))
        else:
            new_sections.append(content)

    return new_sections, seen  # seen = original indices in order of first appearance


def build_daily_archive(data: dict, date_str: str, published_at: str) -> dict:
    """Keep editorial fields and their original (one-based) source indices."""
    validate_daily_report(data)
    keys = ['one_sentence_summary', 'cross_insight', *[key for key, _ in SECTION_DEFS]]
    report = {key: data[key] for key in keys}
    cited_text = '\n'.join(report[key] for key in keys if key != 'one_sentence_summary')
    indices = sorted(set(_citation_indices(cited_text)))
    return {
        'date': date_str,
        'publishedAt': published_at,
        'items': data['items'],
        'report': report,
        **({'qualityAudit': data['qualityAudit']} if 'qualityAudit' in data else {}),
        'selectedItems': [
            {**data['items'][idx - 1], 'citationIndex': idx} for idx in indices
        ],
    }


def save_to_markdown(data, date_str: str | None = None, published_at: str | None = None):
    if date_str is None:
        kst = timezone(timedelta(hours=9))
        date_str = datetime.now(kst).strftime('%Y-%m-%d')
    validate_daily_report(data)

    file_name = f"{date_str}.md"
    dir_path = Path(__file__).parent.parent / 'reports' / 'daily'
    dir_path.mkdir(parents=True, exist_ok=True)

    summary_desc = json.dumps(
        compact_summary(data.get('one_sentence_summary', ''), 45),
        ensure_ascii=False,
    )[1:-1]

    # 인용 번호를 본문 등장 순서 기준으로 재번호 매기기
    section_contents = [data.get('cross_insight', '').strip(), *[data.get(key, '').strip() for key, _ in SECTION_DEFS]]
    renumbered, ordered_orig_indices = _renumber_citations(section_contents)
    covered_count = len(ordered_orig_indices)  # Gemini 자체 집계 대신 실제 인용 수 사용

    # 크로스 인사이트 + 본문 섹션 조합 + 인용 번호 앵커 링크 삽입
    cross_insight = renumbered[0]
    parts = []
    if cross_insight:
        parts.append(f"## 💡 오늘의 관찰\n\n{add_citation_anchors(cross_insight)}")
    for (key, heading), content in zip(SECTION_DEFS, renumbered[1:]):
        if content:
            parts.append(f"## {heading}\n\n{add_citation_anchors(content)}")
    report_body = '\n\n---\n\n'.join(parts)

    # 출처 목록: 등장 순서대로, 순차 번호로 정렬
    all_items = data.get('items', [])
    source_parts = []
    for seq_num, orig_idx in enumerate(ordered_orig_indices, 1):
        if 1 <= orig_idx <= len(all_items):
            item = all_items[orig_idx - 1]
            source_parts.append(source_reference(item, seq_num))
    items_md = '\n\n'.join(source_parts)

    markdown_content = f"""---
date: "{date_str}"
publishedAt: "{published_at or date_str + 'T06:00:00+09:00'}"
title: "데일리 리포트 - {date_str}"
summary: "{summary_desc}"
itemCount: {covered_count}
collectedCount: {len(all_items)}
citedCount: {covered_count}
---

{report_body}

---

### 🔗 출처 및 원문

{items_md}
"""

    file_path = dir_path / file_name
    file_path.write_text(markdown_content, encoding='utf-8')

    print(f"  Saved: reports/daily/{file_name} ({covered_count} items, {len(source_parts)} sources)")
