import feedparser

DEVAI_KEYWORDS = {
    'claude', 'copilot', 'cursor', 'windsurf', 'mcp', 'model context protocol',
    'llm', 'ollama', 'vscode', 'code generation', 'code assist',
    'anthropic', 'gemini api', 'openai api', 'github models',
    'continue', 'litellm', 'langchain', 'local model', 'inference engine',
    'prompt caching', 'rag', 'embedding model', 'fine-tun', 'quantiz',
}


def fetch_rss(url, source_name, limit=3):
    try:
        feed = feedparser.parse(url)
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


def fetch_github_releases(repo, label, limit=1):
    return fetch_rss(f"https://github.com/{repo}/releases.atom", f"GitHub ({label})", limit)


# ── Section 1: 로보틱스 실무 ──────────────────────────────────────

def fetch_arxiv_robotics():
    return fetch_rss('https://export.arxiv.org/rss/cs.RO', 'ArXiv cs.RO', limit=5)

def fetch_ros2_discourse():
    return fetch_rss('https://discourse.ros.org/top/daily.rss', 'ROS2 Discourse', limit=5)

def fetch_ros2_releases():
    repos = [
        ('ros2/rclcpp',                  'rclcpp'),
        ('ros-planning/navigation2',     'Nav2'),
        ('moveit/moveit2',               'MoveIt2'),
        ('gazebosim/gz-sim',             'Gazebo'),
    ]
    items = []
    for repo, label in repos:
        items.extend(fetch_github_releases(repo, label))
    return items


# ── Section 2: AI × 로보틱스 ─────────────────────────────────────

def fetch_arxiv_cv():
    return fetch_rss('https://export.arxiv.org/rss/cs.CV', 'ArXiv cs.CV', limit=3)

def fetch_arxiv_ai():
    return fetch_rss('https://export.arxiv.org/rss/cs.AI', 'ArXiv cs.AI', limit=3)

def fetch_weekly_robotics():
    return fetch_rss('https://weeklyrobotics.com/blog?format=rss', 'Weekly Robotics', limit=3)


# ── Section 3: 개발자 AI 도구 ─────────────────────────────────────

def fetch_simon_willison():
    return fetch_rss('https://simonwillison.net/atom/everything/', 'Simon Willison', limit=3)

def fetch_tldr_ai():
    return fetch_rss('https://tldr.tech/ai/rss', 'TLDR AI', limit=3)

def fetch_hackernews_devai():
    try:
        feed = feedparser.parse('https://news.ycombinator.com/rss')
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


# ── Section 4: 업계 동향 ──────────────────────────────────────────

def fetch_ieee_robotics():
    return fetch_rss('https://spectrum.ieee.org/rss/robotics/fulltext', 'IEEE Spectrum', limit=3)

def fetch_the_robot_report():
    return fetch_rss('https://www.therobotreport.com/feed/', 'The Robot Report', limit=3)
