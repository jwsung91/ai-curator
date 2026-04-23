import os
import json
import re
from datetime import datetime
from google import genai

def generate_summary(items):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in environment variables.")
    
    client = genai.Client(api_key=api_key)
    
    items_text = ""
    for i, item in enumerate(items, 1):
        # truncate summary to avoid huge prompts
        short_desc = item['summary'][:200] + '...' if len(item['summary']) > 200 else item['summary']
        items_text += f"[{i}] {item['title']} ({item['link']})\n  {short_desc}\n\n"
        
    prompt = f"""
당신은 전문 로보틱스 소프트웨어 엔지니어이자 AI 연구원입니다. 
제공된 로보틱스, AI 및 기술 트렌드 정보를 읽고 기술 전문가(로봇 엔지니어)를 위한 전문적인 데일리 큐레이션 리포트를 작성하세요.

작성 지침:
1. 모든 내용은 한국어로 작성하세요.
2. 각 정보 요약 시 반드시 해당 출처의 번호를 대괄호 안에 표기하세요 (예: [1], [2]).
3. 아키텍처 개선, 새로운 알고리즘, ROS 2 통합 가능성 및 주요 산업계 이정표를 중심으로 기술적인 깊이가 있는 요약을 제공하세요.
4. "이것이 엔지니어에게 왜 중요한가(Why this matters)"를 중심으로 인사이트를 포함하세요.

응답은 반드시 아래 두 필드를 가진 JSON 객체 형식이어야 합니다:
- "title": 전문적이고 눈에 띄는 한국어 제목 (예: "로보틱스 & AI 데일리: 새로운 경로 계획 알고리즘과 비전 모델 동향")
- "summary": 구조화된 한국어 마크다운 본문. 글머리 기호와 굵은 글씨를 적절히 사용하세요.

Items:
{items_text}
"""
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt,
        )
        text = response.text
        
        # Try to parse JSON from markdown block
        json_match = re.search(r'```(?:json)?\n(.*?)\n```', text, re.DOTALL)
        if json_match:
            text = json_match.group(1)
            
        return json.loads(text)
    except Exception as e:
        print(f"Error generating summary from Gemini: {e}")
        return {
            "title": "AI 생성 요약 실패",
            "summary": "요약을 생성하는 중 에러가 발생했습니다."
        }

def save_to_markdown(data):
    date_str = datetime.now().strftime('%Y-%m-%d')
    file_name = f"{date_str}-daily.md"
    dir_path = os.path.join(os.getcwd(), 'src', 'content', 'curation')
    
    os.makedirs(dir_path, exist_ok=True)
    
    safe_title = data['title'].replace('"', '\\"')
    
    # First line of summary safely truncated
    first_line = data['summary'].split('\n')[0].replace('"', '\\"')
    short_summary = first_line[:100] + '...' if len(first_line) > 100 else first_line
    
    items_md = "\n".join([f"[{i}] [{item['title']}]({item['link']}) ({item['source']})" for i, item in enumerate(data['items'], 1)])
    
    markdown_content = f"""---
date: "{date_str}"
title: "{safe_title}"
summary: "{short_summary}"
itemCount: {data['itemCount']}
---

{data['summary']}

---

### 🔗 출처 및 원문
{items_md}
"""
    
    file_path = os.path.join(dir_path, file_name)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
        
    print(f"Report saved to src/content/curation/{file_name}")
