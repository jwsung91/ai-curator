import os
import json
import time
from datetime import datetime, timezone, timedelta
from google import genai
from google.genai import errors, types


SECTION_DEFS = [
    ('section_robotics', '🤖 로보틱스 실무'),
    ('section_devtools', '🛠️ 개발자 AI 도구'),
    ('section_industry', '📰 업계 동향'),
]


def build_prompt(items):
    items_text = ""
    for i, item in enumerate(items, 1):
        hint = item.get('section_hint', '')
        items_text += f"[{i}] [{hint}] {item['title']} ({item['link']})\n  {item['summary'][:350]}\n\n"

    return f"""당신은 로봇 시스템에 AI를 통합하는 시니어 소프트웨어 엔지니어입니다.
수집된 기술 정보를 3개 섹션으로 분류하고, 오늘 실무에 바로 적용할 수 있는 데일리 리포트를 작성하세요.

---

## 섹션 분류 기준

**section_robotics — 🤖 로보틱스 실무**
포함: ROS2/Nav2/MoveIt2/Gazebo 릴리스·패치노트, ROS2 커뮤니티 이슈·패키지 업데이트, 임베디드·실시간 시스템
제외: AI 연구, 정책·비즈니스 뉴스

**section_devtools — 🛠️ 개발자 AI 도구**
포함: 오늘 설치·호출 가능한 AI 도구 업데이트, LLM API 변경사항, IDE/코딩 어시스턴트, MCP 서버, 로컬 LLM 추론 도구
제외: 비즈니스 뉴스, 이미 다른 섹션에 포함된 항목

**section_industry — 📰 업계 동향**
포함: 로보틱스·AI 산업 동향, 정책·규제, 기업 투자·인수합병, 신제품 출시
제외: 위 2개 섹션에 포함된 항목, 학술 인물 프로파일, 교육용 하드웨어 프로젝트, 네트워킹 행사·밋업

---

## 작성 규칙

1. 각 항목 형식 (모든 섹션 동일):
   ```
   - **항목명**: 핵심 내용 한 줄 [번호]
     > 💡 인사이트: 구체적인 실무 적용 방법 (패키지명, API, 명령어 포함)
   ```
2. 인사이트는 "무엇을 해야 하는가"가 명확해야 합니다. "~될 것으로 예상된다" 같은 전망은 피하세요.
3. 해당 섹션과 관련 없는 항목은 제외하세요. 관련 항목이 없으면 빈 문자열("")을 반환하세요.
4. covered_count는 3개 섹션 본문에서 실제로 다룬 항목 수의 합입니다.
5. 모든 텍스트는 한국어로 작성하세요 (항목명·패키지명·API명은 원문 유지).

---

## 수집 항목 ({len(items)}개)

{items_text}

---

## 응답 형식

아래 JSON 스키마를 정확히 따르세요:
{{
  "one_sentence_summary": "오늘 가장 중요한 기술 변화 한 문장",
  "section_robotics": "마크다운 내용 (없으면 빈 문자열)",
  "section_devtools": "마크다운 내용 (없으면 빈 문자열)",
  "section_industry": "마크다운 내용 (없으면 빈 문자열)",
  "covered_count": 숫자
}}"""


def generate_summary(items):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=api_key)
    prompt = build_prompt(items)

    model_names = ['gemini-flash-latest']
    last_exception = None

    for model_name in model_names:
        for attempt in range(2):
            try:
                print(f"  🤖 {model_name} (attempt {attempt + 1})")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type='application/json',
                    ),
                )
                data = json.loads(response.text)
                data['items'] = items
                return data
            except (errors.ClientError, errors.ServerError) as e:
                last_exception = e
                err_str = str(e)
                if '429' in err_str or '503' in err_str:
                    if attempt == 0:
                        print(f"  ⚠ Rate limited. Retrying in 30s...")
                        time.sleep(30)
                        continue
                if '404' in err_str or '400' in err_str:
                    print(f"  ⏭ {model_name} unavailable, trying next...")
                    break
                raise e
            except Exception as e:
                print(f"  ✗ {e}")
                last_exception = e
                break

    raise last_exception


def save_to_markdown(data):
    kst = timezone(timedelta(hours=9))
    date_str = datetime.now(kst).strftime('%Y-%m-%d')
    file_name = f"{date_str}-daily.md"
    dir_path = os.path.join(os.getcwd(), 'src', 'content', 'curation')
    os.makedirs(dir_path, exist_ok=True)

    summary_desc = json.dumps(data.get('one_sentence_summary', ''), ensure_ascii=False)[1:-1]
    covered_count = data.get('covered_count', 0)

    parts = []
    for key, heading in SECTION_DEFS:
        content = data.get(key, '').strip()
        if content:
            parts.append(f"## {heading}\n\n{content}")
    report_body = '\n\n---\n\n'.join(parts)

    items_md = "\n\n".join(
        f"{i}. [{item['title']}]({item['link']}) — *{item['source']}*"
        for i, item in enumerate(data.get('items', []), 1)
    )

    markdown_content = f"""---
date: "{date_str}"
title: "{date_str}"
summary: "{summary_desc}"
itemCount: {covered_count}
---

{report_body}

---

### 🔗 출처 및 원문

{items_md}
"""

    file_path = os.path.join(dir_path, file_name)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    print(f"  Saved: src/content/curation/{file_name} ({covered_count} items covered)")
