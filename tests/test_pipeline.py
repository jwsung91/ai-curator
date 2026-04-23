import os
import sys
import json
from unittest.mock import patch, MagicMock

# Add scripts directory to path to import modules
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts'))

from fetcher import fetch_arxiv_trends
from builder import generate_summary, save_to_markdown

def test_fetch_arxiv_trends(mocker):
    # Mock feedparser.parse
    mock_feed = MagicMock()
    
    mock_entry1 = MagicMock()
    mock_entry1.title = "Test Paper 1"
    mock_entry1.link = "http://arxiv.org/abs/1"
    mock_entry1.summary = "This is a test summary 1."
    
    mock_entry2 = MagicMock()
    mock_entry2.title = "Test Paper 2"
    mock_entry2.link = "http://arxiv.org/abs/2"
    mock_entry2.summary = "This is a test summary 2."
    
    mock_feed.entries = [mock_entry1, mock_entry2]
    
    mocker.patch('fetcher.feedparser.parse', return_value=mock_feed)
    
    results = fetch_arxiv_trends()
    
    assert len(results) == 2
    assert results[0]['title'] == "Test Paper 1"
    assert results[0]['source'] == "ArXiv (cs.AI)"

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
