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
    for item in items:
        # truncate summary to avoid huge prompts
        short_desc = item['summary'][:200] + '...' if len(item['summary']) > 200 else item['summary']
        items_text += f"- [{item['title']}]({item['link']})\n  {short_desc}\n\n"
        
    prompt = f"""
You are an expert Robotics Software Engineer and AI Researcher. 
Read the following recent trends from robotics, AI, and tech sources and create a professional daily curation report.

Your goal is to provide insightful summaries for a technical audience (other robotics engineers).
Highlight architectural improvements, new algorithms, ROS 2 integration, and significant industry milestones.

Format your response exactly as a JSON object with two fields:
- "title": A professional and catchy Korean title (e.g., "로보틱스 & AI 데일리: 새로운 경로 계획 알고리즘과 비전 모델 동향")
- "summary": A well-structured Markdown summary in Korean. Use bullet points and bold text to make it readable. Focus on "Why this matters" for engineers.

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
    first_line = data['summary'].split('\\n')[0].replace('"', '\\"')
    short_summary = first_line[:100] + '...' if len(first_line) > 100 else first_line
    
    items_md = "\\n".join([f"- [{item['title']}]({item['link']}) ({item['source']})" for item in data['items']])
    
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
