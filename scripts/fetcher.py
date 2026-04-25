import re
import feedparser
import urllib.request
import urllib.error
from datetime import datetime, timezone

DEVAI_KEYWORDS = {  # HackerNews 필터 키워드
    'claude', 'copilot', 'cursor', 'windsurf', 'mcp', 'model context protocol',
    'llm', 'ollama', 'vscode', 'code generation', 'code assist',
    'anthropic', 'gemini api', 'openai api', 'github models',
    'continue', 'litellm', 'langchain', 'local model', 'inference engine',
    'prompt caching', 'rag', 'embedding model', 'fine-tun', 'quantiz',
}

_HEADERS = {'User-Agent': 'ai-curator/1.0 (github.com/jwsung91/ai-curator)'}


def fetch_rss(url, source_name, limit=3):
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read()
        feed = feedparser.parse(content)
        result = []
        for entry in feed.entries[:limit]:
            result.append({
                'title': getattr(entry, 'title', 'No Title'),
                'link': getattr(entry, 'link', ''),
                'summary': getattr(entry, 'summary', '')[:350],
                'source': source_name,
            })
        return result
    except Exception as e:
        print(f"  ⚠ {source_name}: {e}")
        return []


def fetch_github_releases(repo, label, limit=1, max_age_days=14):
    url = f"https://github.com/{repo}/releases.atom"
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read()
        feed = feedparser.parse(content)
        result = []
        now = datetime.now(timezone.utc)
        for entry in feed.entries[:limit]:
            parsed = getattr(entry, 'updated_parsed', None) or getattr(entry, 'published_parsed', None)
            if parsed:
                age_days = (now - datetime(*parsed[:6], tzinfo=timezone.utc)).days
                if age_days > max_age_days:
                    continue
            body_html = ''
            if hasattr(entry, 'content') and entry.content:
                body_html = entry.content[0].get('value', '')
            elif hasattr(entry, 'summary'):
                body_html = entry.summary
            body_text = re.sub(r'<[^>]+>', ' ', body_html)
            body_text = re.sub(r'\s+', ' ', body_text).strip()[:500]
            result.append({
                'title': f"{label} {getattr(entry, 'title', '').strip()}",
                'link': getattr(entry, 'link', ''),
                'summary': body_text,
                'source': f"GitHub ({label})",
            })
        return result
    except Exception as e:
        print(f"  ⚠ GitHub ({label}): {e}")
        return []


# ── Section 1: 로보틱스 실무 ──────────────────────────────────────

def fetch_ros2_discourse():
    return fetch_rss('https://discourse.ros.org/top/daily.rss', 'ROS2 Discourse', limit=5)

def fetch_ros2_releases():
    repos = [
        ('ros2/rclcpp',              'rclcpp'),
        ('ros-planning/navigation2', 'Nav2'),
        ('moveit/moveit2',           'MoveIt2'),
        ('gazebosim/gz-sim',         'Gazebo'),
        ('ros2/ros2',                'ROS2'),
    ]
    items = []
    for repo, label in repos:
        items.extend(fetch_github_releases(repo, label))
    return items


# ── Section 2: 개발자 AI 도구 ─────────────────────────────────────

def fetch_openai_news():
    return fetch_rss('https://openai.com/news/rss.xml', 'OpenAI News', limit=3)

def fetch_google_deepmind():
    return fetch_rss('https://deepmind.google/blog/rss.xml', 'Google DeepMind', limit=3)


SIMON_KEYWORDS = {
    'llm', 'gpt', 'claude', 'gemini', 'openai', 'anthropic', 'deepseek',
    'mistral', 'llama', 'mcp', 'agent', 'embedding', 'inference', 'fine-tun',
    'prompt', 'multimodal', 'ai model', 'language model', 'vision model',
}

def fetch_simon_willison():
    items = fetch_rss('https://simonwillison.net/atom/everything/', 'Simon Willison', limit=10)
    filtered = [
        item for item in items
        if any(kw in item['title'].lower() for kw in SIMON_KEYWORDS)
    ]
    return filtered[:5]

def fetch_changelog():
    return fetch_rss('https://changelog.com/news/feed', 'The Changelog', limit=3)

def fetch_hackernews_devai():
    try:
        req = urllib.request.Request('https://news.ycombinator.com/rss', headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read()
        feed = feedparser.parse(content)
        matched = []
        for entry in feed.entries:
            if any(kw in entry.title.lower() for kw in DEVAI_KEYWORDS):
                matched.append({
                    'title': entry.title,
                    'link': getattr(entry, 'link', ''),
                    'summary': getattr(entry, 'summary', '')[:350],
                    'source': 'HackerNews',
                })
        return matched[:3]
    except Exception as e:
        print(f"  ⚠ HackerNews: {e}")
        return []

def fetch_devai_releases():
    repos = [
        ('anthropics/anthropic-sdk-python', 'Anthropic SDK'),
        ('modelcontextprotocol/servers',    'MCP Servers'),
        ('ollama/ollama',                   'Ollama'),
        ('continuedev/continue',            'Continue'),
        ('BerriAI/litellm',                 'LiteLLM'),
    ]
    items = []
    for repo, label in repos:
        items.extend(fetch_github_releases(repo, label))
    return items


# ── Section 3: 업계 동향 ──────────────────────────────────────────

def fetch_ieee_robotics():
    return fetch_rss('https://spectrum.ieee.org/rss/robotics/fulltext', 'IEEE Spectrum', limit=3)

def fetch_the_robot_report():
    return fetch_rss('https://www.therobotreport.com/feed/', 'The Robot Report', limit=3)
