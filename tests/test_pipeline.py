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
    fetch_hackernews_trends
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
    setup_mock_feed(mocker, [{"title": "AI Paper", "link": "http://arxiv/1", "summary": "sum"}])
    results = fetch_arxiv_ai_trends()
    assert len(results) == 1
    assert results[0]['source'] == "ArXiv (cs.AI)"

def test_fetch_arxiv_robotics_trends(mocker):
    setup_mock_feed(mocker, [{"title": "Robotics Paper", "link": "http://arxiv/2", "summary": "sum"}])
    results = fetch_arxiv_robotics_trends()
    assert len(results) == 1
    assert results[0]['source'] == "ArXiv (cs.RO)"

def test_fetch_weekly_robotics_trends(mocker):
    setup_mock_feed(mocker, [{"title": "Weekly Robotics", "link": "http://weekly/1", "summary": "sum"}])
    results = fetch_weekly_robotics_trends()
    assert len(results) == 1
    assert results[0]['source'] == "Weekly Robotics"

def test_fetch_ieee_robotics_trends(mocker):
    setup_mock_feed(mocker, [{"title": "IEEE News", "link": "http://ieee/1", "summary": "sum"}])
    results = fetch_ieee_robotics_trends()
    assert len(results) == 1
    assert results[0]['source'] == "IEEE Spectrum"

def test_fetch_ros2_discourse_trends(mocker):
    setup_mock_feed(mocker, [{"title": "ROS2", "link": "http://ros2/1", "summary": "sum"}])
    results = fetch_ros2_discourse_trends()
    assert len(results) == 1
    assert results[0]['source'] == "ROS2 Discourse"

def test_fetch_hackernews_trends(mocker):
    setup_mock_feed(mocker, [{"title": "HN", "link": "http://hn/1", "summary": "sum"}])
    results = fetch_hackernews_trends()
    assert len(results) == 1
    assert results[0]['source'] == "HackerNews"

def test_generate_summary(mocker, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_key")
    mock_genai = mocker.patch('builder.genai')
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_json = {"title": "Title", "summary": "Summary"}
    type(mock_response).text = mocker.PropertyMock(return_value=f"```json\n{json.dumps(mock_json)}\n```")
    mock_client.models.generate_content.return_value = mock_response
    mock_genai.Client.return_value = mock_client
    
    items = [{"title": "T1", "link": "L1", "summary": "S1", "source": "Src1"}]
    result = generate_summary(items)
    assert result['title'] == "Title"

def test_save_to_markdown(tmp_path, mocker):
    mocker.patch('builder.os.getcwd', return_value=str(tmp_path))
    mock_datetime = mocker.patch('builder.datetime')
    mock_date = MagicMock()
    mock_date.strftime.return_value = "2026-04-23"
    mock_datetime.now.return_value = mock_date
    
    test_data = {
        "title": "T", "summary": "S", "itemCount": 1,
        "items": [{"title": "N1", "link": "L", "source": "Src"}]
    }
    save_to_markdown(test_data)
    expected_file = tmp_path / 'src' / 'content' / 'curation' / '2026-04-23-daily.md'
    assert expected_file.exists()
