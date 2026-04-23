import feedparser

def fetch_rss_data(url, source_name, limit=3):
    try:
        feed = feedparser.parse(url)
        items = feed.entries[:limit]
        
        result = []
        for item in items:
            result.append({
                'title': item.title if hasattr(item, 'title') else 'No Title',
                'link': item.link if hasattr(item, 'link') else '',
                'summary': item.summary if hasattr(item, 'summary') else '',
                'source': source_name
            })
        return result
    except Exception as e:
        print(f"Error fetching {source_name} data: {e}")
        return []

def fetch_arxiv_ai_trends():
    return fetch_rss_data('https://export.arxiv.org/rss/cs.AI', 'ArXiv (cs.AI)')

def fetch_arxiv_robotics_trends():
    return fetch_rss_data('https://export.arxiv.org/rss/cs.RO', 'ArXiv (cs.RO)')

def fetch_weekly_robotics_trends():
    return fetch_rss_data('https://weeklyrobotics.com/blog?format=rss', 'Weekly Robotics')

def fetch_ieee_robotics_trends():
    return fetch_rss_data('https://spectrum.ieee.org/rss/robotics/fulltext', 'IEEE Spectrum')

def fetch_ros2_discourse_trends():
    # 'top/daily' RSS for popular topics instead of just latest
    return fetch_rss_data('https://discourse.ros.org/top/daily.rss', 'ROS2 Discourse (Top)')

def fetch_hackernews_trends():
    return fetch_rss_data('https://news.ycombinator.com/rss', 'HackerNews (Top)')

def fetch_github_cpp_trending():
    # Using community RSS for GitHub Trending C++
    return fetch_rss_data('https://github-rss.alexi.sh/trending/daily/cpp', 'GitHub Trending (C++)')

def fetch_github_python_trending():
    # Using community RSS for GitHub Trending Python
    return fetch_rss_data('https://github-rss.alexi.sh/trending/daily/python', 'GitHub Trending (Python)')
