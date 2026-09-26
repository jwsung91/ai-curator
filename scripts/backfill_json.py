#!/usr/bin/env python3
"""기존 daily MD 파일에서 raw items JSON 역생성 (테스트 및 backfill용)"""
import re
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.append(str(Path(__file__).parent))

REPORTS_DIR = Path(__file__).parent.parent / 'reports' / 'daily'

SECTION_KEYWORDS = {
    '로보틱스': '로보틱스',
    'AI':       'AI',
    '트렌드':   '트렌드',
}


class ReferenceParser(HTMLParser):
    """Read escaped reference metadata from both old and new report templates."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        match = re.fullmatch(r'ref-(\d+)', attrs.get('id', ''))
        if tag != 'span' or not match:
            return
        if not all(attrs.get(key) for key in ('data-title', 'data-url', 'data-source')):
            return
        item = {key: attrs[f'data-{attr}'] for key, attr in [('title', 'title'), ('link', 'url'), ('source', 'source')]}
        if attrs.get('data-published-at'):
            item['publishedAt'] = attrs['data-published-at']
        self.refs[int(match.group(1))] = item


def backfill(date_str: str, force: bool = False) -> int:
    md_path   = REPORTS_DIR / f'{date_str}.md'
    json_path = REPORTS_DIR / f'{date_str}.json'

    if not md_path.exists():
        print(f'  ⚠ {date_str}.md not found, skipping')
        return 0
    if json_path.exists() and not force:
        print(f'  ⏭ {date_str}.json already exists (use --force to overwrite)')
        return 0

    content = md_path.read_text(encoding='utf-8')

    # 출처 섹션: "N. [title](url) — *source*"
    refs: dict[int, dict] = {}
    for m in re.finditer(r'(\d+)\. \[([^\]]+)\]\(([^)]+)\) — \*([^*]+)\*', content):
        refs[int(m.group(1))] = {
            'title':  m.group(2),
            'link':   m.group(3),
            'source': m.group(4),
        }
    parser = ReferenceParser()
    parser.feed(content)
    refs.update(parser.refs)

    items: list[dict] = []
    current_section = ''

    for line in content.split('\n'):
        # 섹션 헤더 감지
        if line.startswith('## '):
            current_section = ''
            for kw, hint in SECTION_KEYWORDS.items():
                if kw in line:
                    current_section = hint
                    break

        if not current_section:
            continue

        # 항목 라인에서 ref 번호 추출
        ref_nums = [int(n) for n in re.findall(r'href="#ref-(\d+)"', line)]
        if not ref_nums:
            continue

        # 한 줄 설명 추출: - **Name**: desc ...
        desc_m = re.match(r'-\s+\*\*(.+?)\*\*:\s+(.+?)(?:\s*\[|$)', line)
        desc = desc_m.group(2).strip() if desc_m else ''

        for n in ref_nums:
            if n not in refs:
                continue
            link = refs[n]['link']
            if any(it['link'] == link for it in items):
                continue
            items.append({
                **refs[n],
                'summary':      desc,
                'section_hint': current_section,
            })

    json_path.write_text(
        json.dumps({'date': date_str, 'items': items}, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
    print(f'  ✅ {date_str}.json — {len(items)} items')
    return len(items)


if __name__ == '__main__':
    force = '--force' in sys.argv
    dates = [a for a in sys.argv[1:] if not a.startswith('-')]

    if not dates:
        from weekly_builder import get_week_dates
        kst   = timezone(timedelta(hours=9))
        dates = get_week_dates(datetime.now(kst))
        print(f'이번 주 날짜 자동 감지: {dates[0]} ~ {dates[-1]}')

    total = 0
    for d in dates:
        total += backfill(d, force)
    print(f'\n완료: {len(dates)}일 처리, 총 {total}개 항목')
