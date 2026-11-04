# 인수인계: 꽃 판매 플래너 (2026-11-04)

Claude Code 세션이 이 저장소에서 바로 이어서 작업할 수 있게 정리한 문서예요. 작업 전에 끝까지 읽어 주세요.

## 1. 무엇인가
- 꽃집 사장님이 **학교 졸업식 날짜를 찾아 판매 일정에 담는** 모바일 우선 웹사이트. 첫 정식 오픈 목표 **2026-11-16**.
- 사이트: https://best15993232-sudo.github.io/flower-planner/ (GitHub Pages, main 브랜치 루트를 그대로 배포)
- 사용자(운영자)는 개발자가 아니에요. 보고는 **한국어, 쉬운 말**로 해 주세요. 영어 용어·코드 설명은 최소로.

## 2. 구조
- `index.html` 화면 전체(HTML·CSS·JS 한 파일). 서버 없음, 사용자 데이터는 브라우저 localStorage 에만.
- `privacy.html` 개인정보처리방침·이용약관 초안.
- `config.js` GitHub Actions 가 시크릿으로 만드는 파일(카카오 JS 키). 손대지 말 것.
- `data/places.json`(장소), `data/events.json`(행사) = 사이트가 읽는 파일. **직접 고치지 말고** `scripts/build_events.py` 로 만들어요.
  원본: `data/schools.json`(나이스, 매일 자동 갱신), `data/universities.json`, `data/university_sources.json`(대학 날짜, 사람이 검토한 것만), `data/place_sizes.json`(학생 수), `data/website_status.json`(홈페이지 점검).
- 구조 설명: `docs/data-structure.md`. 대학 조사 자료: `docs/univ-survey/`.
- 자동 작업(.github/workflows): 학사일정 매일 갱신, 홈페이지 점검(매달 1·15일), 대학 주간 점검, config 생성. data-bot 이 data/ 를 커밋하니 **push 전에 항상 `git pull --rebase`**.
- 예약 작업(12/1 밤 대학 재확인 등)은 별도로 걸려 있어요. `docs/univ-survey/` 의 round3 관련 파일은 건드리지 마세요.

## 3. 규칙
- 커밋 메시지는 한국어로 무엇이 바뀌었는지 쉽게. 끝에 저장소 관례대로 `Co-Authored-By` 줄.
- 테스트: `python3 scripts/test_classify.py`, `python3 scripts/test_event_rules.py` (데이터 스크립트 고쳤을 때).
- 화면 확인: 저장소 폴더에서 `python3 -m http.server 8765` → Playwright 로 390×844(휴대폰) 스크린샷. 카카오 지도·장소 검색은 등록된 도메인에서만 동작해서 로컬에서는 안 떠요(정상).
- 배포 확인: push 후 1~2분 뒤 GitHub Pages 반영.
- 비밀값(키·토큰)은 채팅이나 코드에 새로 넣지 마세요. (Cloudflare 방문 통계 토큰은 공개용이라 index.html 에 이미 있음)

## 4. 디자인 기준 (11/2 정리, 이걸로 계속 가요)
- 색 역할: **초록(--brand) = 담기·내 일정만**, **먹색(--ink) = 찾기·필터·선택된 알약**, **회색 = 정보(배지·거리·출처)**. D-day 빨강은 14일 안만.
- 글자 굵기 2단계(700 = 날짜·학교명·큰 숫자, 나머지 400~500). 이모지 대신 선 아이콘 `ic('이름')` (IC 객체에 정의, 로고 🌸만 예외).
- 둥글기: 큰 덩어리 16px(`--r`), 버튼·입력 12px(`--rs`), 알약 999px. 높이: 큰 버튼·입력 50px(`--h`), 작은 버튼·알약 44px(`--hs`).
- 스타일 맨 아래 "디자인 정리" 블록이 최종 규칙이에요. 새 스타일도 이 토큰을 쓰세요.

## 5. 할 일 (위에서부터)
1. **카카오톡 공유 미리보기**: `index.html` `<head>` 에 Open Graph/트위터 메타(제목 "꽃 판매 플래너", 설명 "우리 동네 학교 졸업식 날짜를 한눈에. 담아 두고 꽃다발 수량까지 준비하세요." 정도), 미리보기 이미지 1200×630 PNG(`og.png`, 디자인 기준 색·로고 🌸 느낌, 사람 사진·남의 로고 쓰지 말 것)를 만들어 넣기. 이미지 주소는 절대 경로(https://best15993232-sudo.github.io/flower-planner/og.png). 카카오는 미리보기를 캐시하니 확인 방법(카카오 공유 디버거)을 사용자에게 안내.
2. **홈 화면에 추가(PWA 최소)**: `manifest.webmanifest`(이름, 짧은 이름 "꽃 플래너", 아이콘 192·512, theme/background 색), iOS용 `apple-touch-icon`, `<meta name="theme-color">`. 서비스 워커는 지금은 넣지 않아요(데이터 캐시 꼬임 방지). 아이콘은 🌸 느낌의 단순한 그림을 직접 그려 PNG로.
3. **일정 백업·복원 재검증**: 내 일정 → 백업하기(JSON) → 지우고 → 불러오기가 그대로 되는지 Playwright 로 시험. 예전 형식(`eventId` 없는 항목)도 불러와지는지. 문제 있으면 고치기.
4. **개인정보처리방침 다듬기 준비**: `privacy.html` 의 운영자·문의처·시행일 자리를 정리. 문의 메일은 `contact@bestflower.co.kr`. **운영자 이름(상호)과 시행일은 사용자에게 물어보고** 넣기(추측 금지). 1·2번에서 바뀐 점(공유 이미지 등)이 있으면 반영.

## 6. 끝나면
- 사용자에게 바뀐 점을 짧게(무엇이·어디서 보이는지) 알려 주세요.
- 이 대화(Cowork)에서 노션 체크리스트를 관리하고 있어요. Claude Code 쪽에 노션 연결이 없으면, **노션에 반영할 한두 줄 요약**을 마지막에 따로 적어 주세요(사용자가 Cowork 에 붙여 넣어요).
