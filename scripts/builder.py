import os
import json
import re
import time
from datetime import datetime, timezone, timedelta
from google import genai
from google.genai import errors

def generate_summary(items):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in environment variables.")
    
    client = genai.Client(api_key=api_key)
    
    items_text = ""
    for i, item in enumerate(items, 1):
        short_desc = item['summary'][:200] + '...' if len(item['summary']) > 200 else item['summary']
        items_text += f"[{i}] {item['title']} ({item['link']})\n  {short_desc}\n\n"
        
    prompt = f"""
당신은 전문 로보틱스 소프트웨어 엔지니어이자 AI 연구원입니다. 
제공된 기술 정보를 읽고 동료 엔지니어들이 즉시 업무에 참고할 수 있는 수준의 **전문 데일리 큐레이션 리포트**를 작성하세요.

작성 지침:
1. **언어**: 모든 내용은 한국어로 작성하세요.
2. **리포트 제목 (title)**: 반드시 "YYYY-MM-DD" 형식의 날짜만 작성하세요.
3. **요약 (one_sentence_summary)**: 오늘 수집된 정보 중 가장 중요한 기술적 성취나 트렌드를 **딱 한 문장**으로 요약하여 작성하세요. 이 문장은 리스트 페이지에서 설명(Description)으로 사용됩니다.
4. **본문 (report_body)**: 
   - 줄글(Paragraph)을 최소화하고 **글머리 기호(Bullet points)**를 적극 활용하세요.
   - 주요 기술 용어나 핵심 개념은 **굵게(Bold)** 표시하세요.
   - 각 항목의 요약 바로 아래에 **"> 💡 인사이트:"** 형태의 인용구를 추가하여 실무적 중요성을 설명하세요.
   - 각 요약 내용 끝에 출처 번호를 표기하세요 (예: [1]).

응답은 반드시 아래 세 필드를 가진 JSON 객체 형식이어야 합니다:
{{
  "title": "YYYY-MM-DD",
  "one_sentence_summary": "오늘의 핵심을 관통하는 기술적 요약 한 문장",
  "report_body": "구조화된 마크다운 본문"
}}

Items:
{items_text}
"""
    
    max_retries = 2
    # List of models that are actually available based on client.models.list()
    model_names = ['gemini-flash-latest', 'gemini-2.0-flash', 'gemini-flash-lite-latest']
    
    last_exception = None
    for model_name in model_names:
        for attempt in range(max_retries):
            try:
                print(f"🤖 Trying model: {model_name} (Attempt {attempt+1})")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                text = response.text
                
                # Try to parse JSON from markdown block
                json_match = re.search(r'```(?:json)?\n(.*?)\n```', text, re.DOTALL)
                if json_match:
                    text = json_match.group(1)
                else:
                    first_brace = text.find('{')
                    last_brace = text.rfind('}')
                    if first_brace != -1 and last_brace != -1:
                        text = text[first_brace:last_brace+1]
                
                summary_data = json.loads(text)
                summary_data['items'] = items
                summary_data['itemCount'] = len(items)
                return summary_data
            except (errors.ClientError, errors.ServerError) as e:
                last_exception = e
                if "429" in str(e) or "503" in str(e):
                    if attempt < max_retries - 1:
                        print(f"⚠️ {model_name} Busy. Retrying in 30s...")
                        time.sleep(30)
                        continue
                    else:
                        print(f"⏭️ {model_name} failed. Trying next model...")
                        break
                raise e
            except Exception as e:
                print(f"Error with {model_name}: {e}")
                last_exception = e
                break
    
    if last_exception:
        raise last_exception

def save_to_markdown(data):
    kst = timezone(timedelta(hours=9))
    date_str = datetime.now(kst).strftime('%Y-%m-%d')
    file_name = f"{date_str}-daily.md"
    dir_path = os.path.join(os.getcwd(), 'src', 'content', 'curation')

    os.makedirs(dir_path, exist_ok=True)

    title = date_str
    summary_desc = json.dumps(data.get('one_sentence_summary', ''), ensure_ascii=False)[1:-1]
    
    items_md_list = []
    for i, item in enumerate(data.get('items', []), 1):
        items_md_list.append(f"{i}. [{item['title']}]({item['link']}) — *{item['source']}*")
    items_md = "\n\n".join(items_md_list)
    
    markdown_content = f"""---
date: "{date_str}"
title: "{title}"
summary: "{summary_desc}"
itemCount: {data.get('itemCount', 0)}
---

{data.get('report_body', '')}

---

### 🔗 출처 및 원문

{items_md}
"""
    
    file_path = os.path.join(dir_path, file_name)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
        
    print(f"Report saved to src/content/curation/{file_name}")
