"""Fetch bounded public article excerpts; preserve feed evidence on every failure."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import ipaddress
import json
import socket
import urllib.request
from urllib.parse import urljoin, urlparse

MAX_BYTES = 2_000_000
MAX_TEXT = 12000


def public_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('unsupported URL')
    if parsed.port not in (None, 80, 443):
        raise ValueError('unsupported port')
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80), type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('non-public address')
    return url


class PublicRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, public_url(urljoin(req.full_url, newurl)))


class ArticleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.parts = []
        self.main_parts = []

    def handle_starttag(self, tag, attrs):
        if tag not in ('br', 'img', 'meta', 'link', 'input', 'hr', 'source', 'wbr', 'area', 'base', 'embed', 'param', 'track', 'col'):
            self.stack.append(tag)
        if tag in ('p', 'div', 'li', 'h1', 'h2', 'h3', 'br'):
            self.handle_data('\n')

    def handle_endtag(self, tag):
        if tag in self.stack:
            self.stack = self.stack[:len(self.stack) - 1 - self.stack[::-1].index(tag)]
        self.handle_data('\n')

    def handle_data(self, data):
        if any(tag in self.stack for tag in ('script', 'style', 'nav', 'footer', 'header', 'noscript', 'svg', 'form')):
            return
        self.parts.append(data)
        if 'article' in self.stack or 'main' in self.stack:
            self.main_parts.append(data)

    def text(self):
        return ' '.join(''.join(self.main_parts or self.parts).split())[:MAX_TEXT]


def fetch_article(item):
    result = dict(item)
    if item.get('articleText'):
        return result
    try:
        url = public_url(item.get('link', ''))
        parsed = urlparse(url)
        github = parsed.hostname == 'github.com' and '/releases/tag/' in parsed.path
        if github:
            repository, tag = parsed.path.strip('/').split('/releases/tag/', 1)
            url = public_url(f'https://api.github.com/repos/{repository}/releases/tags/{tag}')
        request = urllib.request.Request(url, headers={'User-Agent': 'ai-curator/1.0', 'Accept': 'application/json' if github else 'text/html'})
        # Ignore proxy environment variables; all redirects are checked too.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), PublicRedirect())
        with opener.open(request, timeout=10) as response:
            content_type = response.headers.get_content_type()
            if content_type not in ('text/html', 'application/xhtml+xml', 'application/json'):
                raise ValueError('unsupported content type')
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError('article too large')
            text = body.decode(response.headers.get_content_charset() or 'utf-8', errors='replace')
            final_url = response.url
        if github:
            release = json.loads(text)
            article = (release.get('body') or '')[:MAX_TEXT]
            result['releaseTag'] = release.get('tag_name', item.get('releaseTag'))
            result['isPrerelease'] = bool(release.get('prerelease'))
            # GitHub release publication is explicitly recorded, never taken from collection time.
            if release.get('published_at'):
                result['publishedAt'] = release['published_at']
        else:
            parser = ArticleText()
            parser.feed(text)
            article = parser.text()
        if len(article.strip()) < 80:
            raise ValueError('insufficient article text')
        result.update(articleText=article, articleUrl=final_url, articleFetchedAt=datetime.now(timezone.utc).isoformat(), articleStatus='fetched')
    except Exception as error:
        result['articleStatus'] = f'unavailable:{type(error).__name__}'
    return result


def enrich_items(items):
    # One attempt per distinct URL in this batch, with bounded concurrency.
    unique = {item.get('link', ''): item for item in items if not item.get('articleText')}
    with ThreadPoolExecutor(max_workers=4) as pool:
        fetched = dict(zip(unique, pool.map(fetch_article, unique.values())))
    fields = ('articleText', 'articleUrl', 'articleFetchedAt', 'articleStatus', 'releaseTag', 'isPrerelease', 'publishedAt')
    return [dict(item, **{k: fetched.get(item.get('link', ''), {}).get(k) for k in fields if k in fetched.get(item.get('link', ''), {})}) if not item.get('articleText') else dict(item) for item in items]
