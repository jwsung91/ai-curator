# AI Curator

로보틱스 소프트웨어 엔지니어를 위한 데일리 기술 큐레이션 사이트.
AI가 매일 KST 06:00에 기술 소식을 수집·분류·요약하여 GitHub Pages에 자동 배포합니다.

**→ [jwsung91.github.io/ai-curator](https://jwsung91.github.io/ai-curator)**

## 아키텍처

```
GitHub Actions (매일 KST 06:00)
  └─ scripts/main.py
       ├─ fetcher.py   RSS 수집 (ROS2, GitHub Releases, HN, Simon Willison 등)
       ├─ 중복 제거    seen_links.json 7일 롤링 윈도우
       └─ builder.py  Gemini Flash API → 한국어 요약 + 섹션 분류
            └─ src/content/curation/YYYY-MM-DD-daily.md 생성
  └─ npm run build (Astro SSG)
  └─ GitHub Pages 배포
```

## 콘텐츠 구성

리포트는 3개 섹션으로 구성됩니다.

| 섹션 | 소스 |
|------|------|
| 🤖 로보틱스 실무 | ROS2 Discourse, GitHub Releases (rclcpp / Nav2 / MoveIt2 / Gazebo / ROS2) |
| 🛠️ 개발자 AI 도구 | Simon Willison, The Changelog, HackerNews (키워드 필터), GitHub Releases (Anthropic SDK / MCP Servers / Ollama / Continue / LiteLLM) |
| 📰 업계 동향 | IEEE Spectrum Robotics, The Robot Report |

## 프로젝트 구조

```
scripts/
  main.py           파이프라인 진입점 (수집 → 중복제거 → 요약 → 저장)
  fetcher.py        RSS/Atom 수집 함수
  builder.py        Gemini API 호출 및 마크다운 생성
  seen_links.json   중복 방지용 최근 7일 링크 목록
  requirements.txt

src/
  content/curation/ 자동 생성된 마크다운 리포트
  pages/
    index.astro     리포트 목록
    curation/[id].astro  리포트 상세 (TOC 포함)
  layouts/BaseLayout.astro  헤더 / 다크모드 / RSS 링크
  styles/global.css

.github/workflows/deploy.yml  스케줄 + 빌드 + 배포
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
