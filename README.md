# ai-curator

AI가 기술 소식을 수집·요약해 매일 데일리 리포트로 제공하는 큐레이션 사이트.
[jwsung91.github.io/ai-curator](https://jwsung91.github.io/ai-curator/) — [Astro](https://astro.build) 기반 정적 사이트, GitHub Pages 배포.

> 현재 개발 중입니다.

## Stack

- **Framework:** Astro 6.1.8 (Static)
- **Styling:** Tailwind CSS v4 (`@tailwindcss/vite`)
- **Fonts:** JetBrains Mono, Pretendard
- **AI:** Claude (Haiku) / Gemini (Flash) — 예정
- **Deploy:** GitHub Actions → GitHub Pages (매일 KST 10:00 자동 빌드)

## 구현 계획

### 데이터 흐름

```
GitHub Actions (daily cron)
  → scripts/generate.ts
    → 소스 수집 (HN, RSS 등)
    → Claude / Gemini API 호출 (요약·분류)
    → src/content/reports/YYYY-MM-DD.md 생성
  → astro build → GitHub Pages 배포
```

### 라우팅 (예정)

| 경로 | 설명 |
|------|------|
| `/ai-curator/` | 최신 리포트 + 아카이브 목록 |
| `/ai-curator/YYYY-MM-DD` | 날짜별 리포트 상세 |

### 콘텐츠 스키마

```yaml
---
date: "YYYY-MM-DD"
title: "Daily Digest — YYYY.MM.DD"
summary: 한 줄 요약
itemCount: 10
---
```

## 개발

```bash
npm install
npm run dev      # localhost:4321/ai-curator/
npm run build    # dist/ 생성
```

Node.js 22 이상 필요.

## 아키텍처 메모

이 레포는 독립 운영. 나머지 서브패스:

- `/` — 커리어 허브 + 블로그 ([jwsung91/jwsung91.github.io](https://github.com/jwsung91/jwsung91.github.io))
- `/unilink/` — 라이브러리 문서 ([jwsung91/unilink](https://github.com/jwsung91/unilink))
