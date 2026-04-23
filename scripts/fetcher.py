import feedparser

def fetch_rss_data(url, source_name, limit=5):
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
    return fetch_rss_data('https://export.arxiv.org/rss/cs.AI', 'ArXiv (cs.AI)', limit=3)

def fetch_arxiv_robotics_trends():
    return fetch_rss_data('https://export.arxiv.org/rss/cs.RO', 'ArXiv (cs.RO)', limit=3)

def fetch_weekly_robotics_trends():
    return fetch_rss_data('https://weeklyrobotics.com/blog?format=rss', 'Weekly Robotics', limit=3)

def fetch_ieee_robotics_trends():
    return fetch_rss_data('https://spectrum.ieee.org/rss/robotics/fulltext', 'IEEE Spectrum', limit=3)

def fetch_ros2_discourse_trends():
    return fetch_rss_data('https://discourse.ros.org/latest.rss', 'ROS2 Discourse', limit=2)

def fetch_hackernews_trends():
    return fetch_rss_data('https://news.ycombinator.com/rss', 'HackerNews', limit=2)
