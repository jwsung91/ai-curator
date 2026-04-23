import feedparser

def fetch_arxiv_trends():
    try:
        url = 'https://export.arxiv.org/rss/cs.AI'
        feed = feedparser.parse(url)
        # Fetch only the top 5 for the daily summary
        items = feed.entries[:5]
        
        result = []
        for item in items:
            result.append({
                'title': item.title if hasattr(item, 'title') else 'No Title',
                'link': item.link if hasattr(item, 'link') else '',
                'summary': item.summary if hasattr(item, 'summary') else '',
                'source': 'ArXiv (cs.AI)'
            })
        return result
    except Exception as e:
        print(f"Error fetching ArXiv data: {e}")
        return []
