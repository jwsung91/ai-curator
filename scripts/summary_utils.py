def compact_summary(text: str, max_chars: int) -> str:
    """Keep report summaries short enough to work as subtitles."""
    summary = ' '.join((text or '').split()).strip()
    summary = summary.rstrip('.。.!?…')
    if len(summary) <= max_chars:
        return summary

    return summary[:max_chars].rstrip(' ,，、·-') + '…'
