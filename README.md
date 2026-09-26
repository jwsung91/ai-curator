# AI Curator

로보틱스 소프트웨어 엔지니어를 위한 데일리 기술 큐레이션 사이트.
AI가 월~금 KST 06:00에 로보틱스/AI 기술 소식을 수집·분류·요약하여 GitHub Pages에 자동 배포합니다.

**→ [jwsung91.github.io/ai-curator](https://jwsung91.github.io/ai-curator)**

## 아키텍처

```
GitHub Actions (월~금 06:00 / 매주 토 09:00 KST)
  └─ scripts/
       ├─ main.py (Daily)      RSS 수집 → Gemini 요약 → reports/daily/ 생성
       └─ weekly_main.py (Weekly) 데일리 데이터 취합 → Gemini 분석 → reports/weekly/ 생성
  └─ npm run build (Astro SSG)
  └─ GitHub Pages 배포
```

## 콘텐츠 구성

리포트는 크게 두 가지 유형으로 제공됩니다.

- **Daily Reports**: 월~금 KST 06:00에 로보틱스/AI 기술 소식을 빠른 operational digest로 발행합니다.
- **Weekly Reports**: 월~금 리포트를 모아 토요일 KST 09:00에 한 주의 흐름과 섹션별 하이라이트를 제공합니다.
- **Monthly Reports**: 자동화하지 않으며, 필요할 때 별도 회고 글로 작성합니다.

| 섹션 | 소스 |
|------|------|
| 🤖 로보틱스 하이라이트 | ROS2 Discourse, ROS2/Gazebo/Nav2/MoveIt2 Releases, DDS/RMW/rosbag2/Open-RMF, Isaac ROS, NVIDIA Developer Blog |
| ✨ AI 도구 하이라이트 | OpenAI News, Google DeepMind, Simon Willison, HackerNews, GitHub (Ollama, LiteLLM, MCP Servers 등) |
| 📈 트렌드 하이라이트 | IEEE Spectrum, The Robot Report, NVIDIA Blog |

## 프로젝트 구조

```
reports/
  daily/            자동 생성된 데일리 리포트 (Markdown + JSON)
  weekly/           자동 생성된 위클리 리포트 (Markdown)

scripts/
  main.py           데일리 파이프라인 진입점
  weekly_main.py    위클리 파이프라인 진입점
  fetcher.py        RSS/Atom 수집 및 필터링
  builder.py        데일리 리포트 생성 로직
  weekly_builder.py 위클리 리포트 생성 로직
  seen_links.json   중복 방지용 링크 저장소

src/
  pages/
    index.astro     최신 데일리·위클리 홈 (/)
    search.astro    본문 검색·주제·유형·발행 월 필터
    about.astro     정보 소스·편집 기준·구독 안내
    weekly/
      index.astro   위클리 리포트 아카이브 (/weekly)
      [id].astro    위클리 상세 페이지
    curation/
      [id].astro    데일리 상세 페이지
  layouts/BaseLayout.astro  공통 레이아웃 및 네비게이션
```

## 로컬 실행

```bash
# Python 파이프라인
python3 -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt
export GEMINI_API_KEY=your_key
python scripts/main.py

# 프론트엔드
npm install
npm run dev
```

## 환경 변수

GitHub Actions에 등록 필요:

| Secret | 설명 |
|--------|------|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) 발급 |

## 기술 스택

- **Python**: feedparser, google-genai
- **Frontend**: Astro 7, Tailwind CSS v4, @tailwindcss/typography
- **CI/CD**: GitHub Actions, stefanzweifel/git-auto-commit-action

## 탐색과 편집 기준

- `/search/`: 기존 데일리·위클리의 제목, 본문, 출처를 검색합니다. 주제·리포트 유형·발행 월 필터를 함께 적용할 수 있으며, 검색 조건은 URL에 보존됩니다. 결과는 12개씩 표시합니다.
- 주제는 본문 키워드로 자동 분류하는 보조 탐색 수단입니다. 뉴스별 수동 분류나 완전한 기술 분류 체계를 의미하지 않습니다.
- 데일리와 해당 기간의 위클리는 서로 연결됩니다. 아직 위클리가 없는 날짜에는 링크를 표시하지 않습니다.
- `/about/`에서 출처 유형, 자동 요약의 범위, 발행 일정과 RSS 구독 방법을 안내합니다.
- 수집 시 HTML을 정리한 최대 1,200자의 요약과 원문 발행·수정일을 보존합니다. 댓글 링크만 있는 요약은 빈 근거로 취급하고, 모델에 제목 기반임을 표시하도록 지시합니다. 이후 공개 원문에서 최대 12,000자의 본문 발췌를 추가로 확보합니다. 원문 접근 실패·본문 추출 실패는 항목에 기록하고 피드 근거로 계속 처리합니다.
- GitHub 릴리스는 제목 대신 URL의 태그로 프리릴리스를 판별하고, 피드 내 다음 안정판 후보를 탐색합니다. 원문 보강 단계에서는 GitHub Releases API의 본문·발행 시각·prerelease 플래그도 보존합니다. API 접근이 실패하면 피드의 태그 기반 정보가 유지됩니다.
- 관찰·주간 흐름의 인용도 본문과 함께 검증·재번호화합니다. 원문 발행일을 모르면 리포트 날짜로 대체하지 않습니다.
- 새 데일리 JSON은 원시 `items`와 함께 편집 결과 `report`, 인용된 원시 항목 `selectedItems`를 저장합니다. `citationIndex`는 `report`에서 사용한 원래 `items`의 1부터 시작하는 번호입니다. 화면용 Markdown은 등장 순서로 다시 번호를 매깁니다. 기존 JSON은 재생성하지 않으며 주간 파이프라인과 호환됩니다.

## 검증

```bash
python3 -m pytest -q
node --experimental-strip-types --test tests/discovery.test.ts
npm run build
```

Python 테스트 실행에는 개발 환경에 `pytest`가 필요합니다. 테스트는 실제 Gemini API를 호출하지 않습니다.

## 프롬프트 편집 기준

데일리·위클리는 `scripts/quality_pipeline.py`에서 **선별·근거 추출 → 작성 → 원문 대조·수정**의 세 단계로 생성합니다. 단계별로 별도 모델 호출을 사용합니다. 원문에 있는 근거 구절을 추출하고, 모든 입력의 선정·제외 이유를 남깁니다. 유용한 기능 설명과 튜토리얼을 보존하기 위해 섹션별 항목 수 상한을 두지 않습니다.

작성 근거에는 수집 시각을 전달하지 않습니다. 출력의 사건 날짜는 인용한 원문에 있는 ISO 날짜인지 검사하며, 최종 검토에서 선정 항목을 제거하면 이유가 필요합니다. 날짜·형식·근거 구절 검증 실패는 한 번 재요청하고, 재차 실패하거나 검토 미완료이면 발행을 중단합니다.

데일리 JSON과 새 위클리 JSON에 `qualityAudit`으로 선정 계획·초안·검토 수정 내역·단계별 원본 응답을 보존합니다. 원문의 진실성이나 모든 문장의 의미적 일치를 자동 검증만으로 보장하지는 않습니다. 위클리는 당시 저장한 데일리 근거를 재사용하며 과거 기사 원문을 새로 수집해 끼워 넣지 않습니다.

`build_prompt` 등 이전 단일 호출용 함수는 평가 호환을 위해 남아 있으며 운영 생성 경로는 위의 세 단계 파이프라인입니다.

구체적인 변경 이유, 검토 시나리오와 검증 범위는 [프롬프트 검토 기록](docs/prompt-review.md)을 참고하세요.
