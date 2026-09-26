"""Normalize feed evidence without inventing missing article content."""
from datetime import datetime, timezone
from html.parser import HTMLParser
import re
from urllib.parse import unquote, urlparse


class _TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag in ('p', 'br', 'div', 'li'):
            self.parts.append(' ')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)
        self.parts.append(' ')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def clean_summary(value: str, limit: int = 1200) -> str:
    parser = _TextParser()
    parser.feed(value or '')
    text = re.sub(r'\s+', ' ', ''.join(parser.parts)).strip()
    return '' if text.casefold() in ('comments', 'comments:') else text[:limit]


def entry_dates(entry) -> dict:
    result = {}
    for source, target in [('published_parsed', 'publishedAt'), ('updated_parsed', 'updatedAt')]:
        parsed = getattr(entry, source, None)
        if parsed:
            result[target] = datetime(*parsed[:6], tzinfo=timezone.utc).isoformat()
    return result


def release_metadata(title: str, link: str) -> dict:
    path = unquote(urlparse(link).path)
    tag = path.split('/releases/tag/', 1)[-1] if '/releases/tag/' in path else title
    prerelease = bool(re.search(r'(?:^|[-.\d])(rc\d*|alpha\d*|beta\d*|dev\d*|nightly)(?:[.\d-]|$)', tag, re.I))
    return {'releaseTag': tag, 'isPrerelease': prerelease}


def evidence_text(item: dict) -> str:
    summary = clean_summary(item.get('summary', ''))
    metadata = []
    if item.get('publishedAt'):
        metadata.append(f"원문 발행: {item['publishedAt']}")
    release = release_metadata(item.get('title', ''), item.get('link', '')) if '/releases/tag/' in item.get('link', '') else {}
    if item.get('releaseTag') or release:
        metadata.append(f"릴리스 태그: {item.get('releaseTag', release.get('releaseTag'))}")
        if item.get('isPrerelease') or release.get('isPrerelease'):
            metadata.append('프리릴리스 — 안정판으로 소개하지 마세요')
    return '\n  '.join([summary or '본문 근거 없음 — 제목에 명시된 사실만 전달하세요', *metadata])


def source_reference(item: dict, number: int) -> str:
    from html import escape
    title = escape(item['title'], quote=True)
    link = escape(item['link'], quote=True)
    source = escape(item['source'], quote=True)
    date = escape(item.get('publishedAt', ''))
    date_label = f' · 원문 발행: {date}' if date else ' · 원문 발행일 미상'
    return (
        f'<span id="ref-{number}" data-title="{title}" data-url="{link}" data-source="{source}" data-published-at="{date}"></span>\n\n'
        f'<p>{number}. <a href="{link}">{title}</a> — <em>{source}</em>{date_label}</p>'
    )
