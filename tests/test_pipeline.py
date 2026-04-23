import os
import sys
import json
from unittest.mock import patch, MagicMock

# Add scripts directory to path to import modules
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts'))

from fetcher import (
    fetch_arxiv_ai_trends, 
    fetch_arxiv_robotics_trends, 
    fetch_weekly_robotics_trends, 
    fetch_ieee_robotics_trends,
    fetch_ros2_discourse_trends, 
    fetch_hackernews_trends,
    fetch_github_cpp_trending,
    fetch_github_python_trending
)
from builder import generate_summary, save_to_markdown

def setup_mock_feed(mocker, entries_data):
    mock_feed = MagicMock()
    mock_entries = []
    for entry in entries_data:
        m_entry = MagicMock()
        m_entry.title = entry['title']
        m_entry.link = entry['link']
        m_entry.summary = entry['summary']
        mock_entries.append(m_entry)
    mock_feed.entries = mock_entries
    mocker.patch('fetcher.feedparser.parse', return_value=mock_feed)

def test_fetch_arxiv_ai_trends(mocker):
    setup_mock_feed(mocker, [{"title": "AI", "link": "L", "summary": "S"}])
    results = fetch_arxiv_ai_trends()
    assert results[0]['source'] == "ArXiv (cs.AI)"

def test_fetch_arxiv_robotics_trends(mocker):
    setup_mock_feed(mocker, [{"title": "Robotics", "link": "L", "summary": "S"}])
    results = fetch_arxiv_robotics_trends()
    assert results[0]['source'] == "ArXiv (cs.RO)"

def test_fetch_ros2_discourse_trends(mocker):
    setup_mock_feed(mocker, [{"title": "ROS2", "link": "L", "summary": "S"}])
    results = fetch_ros2_discourse_trends()
    assert results[0]['source'] == "ROS2 Discourse (Top)"

def test_fetch_github_cpp_trending(mocker):
    setup_mock_feed(mocker, [{"title": "CppRepo", "link": "L", "summary": "S"}])
    results = fetch_github_cpp_trending()
    assert results[0]['source'] == "GitHub Trending (C++)"

def test_fetch_github_python_trending(mocker):
    setup_mock_feed(mocker, [{"title": "PyRepo", "link": "L", "summary": "S"}])
    results = fetch_github_python_trending()
    assert results[0]['source'] == "GitHub Trending (Python)"

def test_generate_summary(mocker, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_key")
    mock_genai = mocker.patch('builder.genai')
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_json = {
        "title": "2026-04-23", 
        "one_sentence_summary": "One sentence summary.",
        "report_body": "Report Body"
    }
    type(mock_response).text = mocker.PropertyMock(return_value=f"```json\n{json.dumps(mock_json)}\n```")
    mock_client.models.generate_content.return_value = mock_response
    mock_genai.Client.return_value = mock_client
    
    items = [{"title": "T", "link": "L", "summary": "S", "source": "Src"}]
    result = generate_summary(items)
    assert result['title'] == "2026-04-23"
    assert result['one_sentence_summary'] == "One sentence summary."

def test_save_to_markdown(tmp_path, mocker):
    mocker.patch('builder.os.getcwd', return_value=str(tmp_path))
    mock_datetime = mocker.patch('builder.datetime')
    mock_date = MagicMock()
    mock_date.strftime.return_value = "2026-04-23"
    mock_datetime.now.return_value = mock_date
    
    test_data = {
        "title": "2026-04-23", 
        "one_sentence_summary": "One sentence summary.",
        "report_body": "Report Body",
        "items": [{"title": "N1", "link": "L", "source": "Src"}],
        "itemCount": 1
    }
    save_to_markdown(test_data)
    expected_file = tmp_path / 'src' / 'content' / 'curation' / '2026-04-23-daily.md'
    assert expected_file.exists()
    content = expected_file.read_text()
    assert 'summary: "One sentence summary."' in content
