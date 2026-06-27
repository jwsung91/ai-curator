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
    index.astro     데일리 리포트 아카이브 (/)
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
- **Frontend**: Astro 6, Tailwind CSS v4, @tailwindcss/typography
- **CI/CD**: GitHub Actions, stefanzweifel/git-auto-commit-action
