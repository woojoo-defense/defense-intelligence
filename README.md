# 방산MICE 글로벌 마켓 인텔리전스

해외 조달공고·글로벌 공급망·전시회 정보를 국내 방산기업의 **수출기회**로 바꿔 전달하는
주간 인텔리전스 서비스입니다. 2026년 1월 5일 창간, 매주 월요일 발행.

- 소개·작동방식·아카이브·전시회 캘린더를 담은 웹사이트 (React + Vite)
- 실제 발송한 주간 뉴스레터 원본 HTML 아카이브
- 수집·채점·검증·발행 파이프라인 (Python, `newsletter-system/`)

## 구조

```
├─ src/                    사이트 (React + Vite)
├─ public/
│   ├─ issues/*.html       주간호 뉴스레터 원본
│   ├─ data/issues.json    아카이브 색인
│   ├─ data/sources.json   정보원 목록
│   └─ logos/              정보원 로고
└─ newsletter-system/      수집·발행 파이프라인 (Python)
```

## 정보원

| 계층 | 소스 |
|---|---|
| 공식 조달 | TED(EU 27개국) · SAM.gov(미국) · U.S. DoD · UK MOD/DE&S · Find a Tender(영국) · CanadaBuys(캐나다) |
| 전문매체 | Defense News · Breaking Defense · Defense One · Naval News · DefenseScoop · Defence Industry Europe 외 |
| 지역 | IDRW · Bharat Shakti · Livefist · StratNews(인도) · Arab News · The National(중동) · 국방신문(국내) |
| 연구·오피니언 | OpenAlex · War on the Rocks · Atlantic Council · Lowy Interpreter · Modern War Institute 외 |
| 타깃 검색 | Google News 30개 쿼리 (국가·품목·OEM별) |

## 수록 원칙

- 기사 본문을 복제하지 않습니다. 제목·공개 요약·URL·발행일·출처만 저장합니다.
- 유료·로그인 콘텐츠는 수집하지 않습니다.
- 자동 요약을 그대로 발행하지 않습니다. 원문 대조 후 사람이 다시 씁니다.
- 정보 신뢰등급(A~E)을 함께 표기하며 E등급은 발행하지 않습니다.
- 발행 전 모든 링크의 생존을 확인합니다.

## 개발

```bash
npm install
npm run dev      # 로컬 개발 서버
npm run build    # dist/ 생성
```

배포는 Vercel (Vite 자동 감지, 빌드 명령 `npm run build`, 출력 `dist`).
