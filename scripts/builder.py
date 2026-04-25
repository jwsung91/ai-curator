import os
import re
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


def add_citation_anchors(text: str) -> str:
    """[1] 또는 [2, 3, 4] 형태의 인용 번호를 앵커 링크로 변환."""
    def replace_bracket(m):
        nums = [n.strip() for n in m.group(1).split(',')]
        linked = ', '.join(
            f'<a href="#ref-{n}">{n}</a>' for n in nums if n.isdigit()
        )
        return f'[{linked}]'
    # 마크다운 링크 [text](url) 와 이미지 ![](url)는 제외
    return re.sub(r'(?<!!)\[(\d+(?:,\s*\d+)*)\](?!\()', replace_bracket, text)


def build_prompt(items):
    items_text = ""
    for i, item in enumerate(items, 1):
        hint = item.get('section_hint', '')
        items_text += f"[{i}] [{hint}] {item['title']} ({item['link']})\n  {item['summary'][:350]}\n\n"

    return f"""당신은 로봇 시스템에 AI를 통합하는 시니어 소프트웨어 엔지니어입니다.
수집된 기술 정보를 3개 섹션으로 분류하고, 오늘 실무에 참고할 수 있는 데일리 리포트를 작성하세요.

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
   ```
2. 해당 섹션과 관련 없는 항목은 제외하세요. 관련 항목이 없으면 빈 문자열("")을 반환하세요.
3. covered_count는 3개 섹션 본문에서 실제로 다룬 항목 수의 합입니다.
4. used_indices는 본문의 [번호] 인용에 실제로 사용된 번호를 중복 없이 오름차순으로 나열하세요.
5. cross_insight는 오늘 3개 섹션을 가로질러 보이는 큰 흐름을 **정확히 3개의 불릿**으로 서술하세요. 각 불릿은 한 문장이며, 단순 항목 재진술이 아닌 섹션 간 연결고리나 공통 맥락을 짚어야 합니다. 형식: "- 문장1\n- 문장2\n- 문장3"
6. 모든 텍스트는 한국어로 작성하세요 (항목명·패키지명·API명은 원문 유지).

---

## 수집 항목 ({len(items)}개)

{items_text}

---

## 응답 형식

아래 JSON 스키마를 정확히 따르세요:
{{
  "one_sentence_summary": "오늘 가장 중요한 기술 변화 한 문장",
  "cross_insight": "- 문장1\n- 문장2\n- 문장3",
  "section_robotics": "마크다운 내용 (없으면 빈 문자열)",
  "section_devtools": "마크다운 내용 (없으면 빈 문자열)",
  "section_industry": "마크다운 내용 (없으면 빈 문자열)",
  "covered_count": 숫자,
  "used_indices": [1, 2, 3]
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


def _renumber_citations(section_contents):
    """Renumber [N] citations to sequential order of first appearance across sections."""
    combined = '\n'.join(c for c in section_contents if c)

    seen = []
    for m in re.finditer(r'(?<!!)\[(\d+(?:,\s*\d+)*)\](?!\()', combined):
        for n_str in m.group(1).split(','):
            n_str = n_str.strip()
            if n_str.isdigit():
                idx = int(n_str)
                if idx not in seen:
                    seen.append(idx)

    mapping = {old: new for new, old in enumerate(seen, 1)}

    def replace_nums(m):
        nums = [n.strip() for n in m.group(1).split(',')]
        replaced = [str(mapping.get(int(n), n)) if n.isdigit() else n for n in nums]
        return f'[{", ".join(replaced)}]'

    new_sections = []
    for content in section_contents:
        if content:
            new_sections.append(re.sub(r'(?<!!)\[(\d+(?:,\s*\d+)*)\](?!\()', replace_nums, content))
        else:
            new_sections.append(content)

    return new_sections, seen  # seen = original indices in order of first appearance


def save_to_markdown(data):
    kst = timezone(timedelta(hours=9))
    date_str = datetime.now(kst).strftime('%Y-%m-%d')
    file_name = f"{date_str}.md"
    dir_path = os.path.join(os.getcwd(), 'reports', 'daily')
    os.makedirs(dir_path, exist_ok=True)

    summary_desc = json.dumps(data.get('one_sentence_summary', ''), ensure_ascii=False)[1:-1]
    covered_count = data.get('covered_count', 0)

    # 인용 번호를 본문 등장 순서 기준으로 재번호 매기기
    section_contents = [data.get(key, '').strip() for key, _ in SECTION_DEFS]
    renumbered, ordered_orig_indices = _renumber_citations(section_contents)

    # 크로스 인사이트 + 본문 섹션 조합 + 인용 번호 앵커 링크 삽입
    cross_insight = data.get('cross_insight', '').strip()
    parts = []
    if cross_insight:
        parts.append(f"💡 **오늘의 흐름**\n\n{cross_insight}")
    for (key, heading), content in zip(SECTION_DEFS, renumbered):
        if content:
            parts.append(f"## {heading}\n\n{add_citation_anchors(content)}")
    report_body = '\n\n---\n\n'.join(parts)

    # 출처 목록: 등장 순서대로, 순차 번호로 정렬
    all_items = data.get('items', [])
    source_parts = []
    for seq_num, orig_idx in enumerate(ordered_orig_indices, 1):
        if 1 <= orig_idx <= len(all_items):
            item = all_items[orig_idx - 1]
            source_parts.append(
                f'<span id="ref-{seq_num}"></span>\n\n'
                f'{seq_num}. [{item["title"]}]({item["link"]}) — *{item["source"]}*'
            )
    items_md = '\n\n'.join(source_parts)

    markdown_content = f"""---
date: "{date_str}"
title: "데일리 리포트 - {date_str}"
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

    print(f"  Saved: reports/daily/{file_name} ({covered_count} items, {len(source_parts)} sources)")
