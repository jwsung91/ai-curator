import os
import sys
import json
from unittest.mock import patch, MagicMock

# Add scripts directory to path to import modules
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts'))

from fetcher import fetch_arxiv_trends, fetch_ros2_discourse_trends, fetch_hackernews_trends
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

def test_fetch_arxiv_trends(mocker):
    setup_mock_feed(mocker, [
        {"title": "ArXiv Paper", "link": "http://arxiv/1", "summary": "ArXiv Summary"}
    ])
    results = fetch_arxiv_trends()
    assert len(results) == 1
    assert results[0]['title'] == "ArXiv Paper"
    assert results[0]['source'] == "ArXiv (cs.AI)"

def test_fetch_ros2_discourse_trends(mocker):
    setup_mock_feed(mocker, [
        {"title": "ROS2 News", "link": "http://ros2/1", "summary": "ROS2 Summary"}
    ])
    results = fetch_ros2_discourse_trends()
    assert len(results) == 1
    assert results[0]['title'] == "ROS2 News"
    assert results[0]['source'] == "ROS2 Discourse"

def test_fetch_hackernews_trends(mocker):
    setup_mock_feed(mocker, [
        {"title": "HN Post", "link": "http://hn/1", "summary": "HN Summary"}
    ])
    results = fetch_hackernews_trends()
    assert len(results) == 1
    assert results[0]['title'] == "HN Post"
    assert results[0]['source'] == "HackerNews"

def test_generate_summary(mocker, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy_key")
    
    mock_genai = mocker.patch('builder.genai')
    mock_client = MagicMock()
    mock_response = MagicMock()
    
    mock_json = {
        "title": "테스트 요약 타이틀",
        "summary": "이것은 테스트 요약입니다."
    }
    
    # Mock text property
    type(mock_response).text = mocker.PropertyMock(return_value=f"```json\n{json.dumps(mock_json)}\n```")
    mock_client.models.generate_content.return_value = mock_response
    mock_genai.Client.return_value = mock_client
    
    items = [
        {"title": "Paper 1", "link": "link1", "summary": "sum1", "source": "src1"}
    ]
    
    result = generate_summary(items)
    
    assert result['title'] == "테스트 요약 타이틀"
    assert "이것은 테스트 요약입니다." in result['summary']

def test_save_to_markdown(tmp_path, mocker):
    # Mock os.getcwd to return tmp_path so it writes to the temp directory
    mocker.patch('builder.os.getcwd', return_value=str(tmp_path))
    
    # Mock datetime to ensure consistent date
    mock_datetime = mocker.patch('builder.datetime')
    mock_date = MagicMock()
    mock_date.strftime.return_value = "2026-04-23"
    mock_datetime.now.return_value = mock_date
    
    test_data = {
        "title": "테스트 리포트",
        "summary": "첫 번째 줄\n두 번째 줄",
        "itemCount": 1,
        "items": [
            {"title": "논문 1", "link": "http://link", "source": "ArXiv"}
        ]
    }
    
    save_to_markdown(test_data)
    
    expected_dir = tmp_path / 'src' / 'content' / 'curation'
    expected_file = expected_dir / '2026-04-23-daily.md'
    
    assert expected_file.exists()
    
    content = expected_file.read_text(encoding='utf-8')
    assert 'title: "테스트 리포트"' in content
    assert 'itemCount: 1' in content
    assert '첫 번째 줄\n두 번째 줄' in content
    assert '[논문 1](http://link) (ArXiv)' in content
