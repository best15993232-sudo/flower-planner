꽃 판매 플래너 배포 폴더
- index.html        : 화면 (이 파일은 거의 안 바뀌어요)
- data/schools.json : 학교·졸업일 데이터 (주간 수집 스크립트가 이 파일만 교체)
- preview_single_file.html : 더블클릭으로 바로 볼 수 있는 미리보기용 (실제 배포에는 쓰지 않아요)

주의: index.html을 파일로 직접 열면 브라우저가 데이터 파일을 막아서 "불러오지 못했어요"가 떠요.
정적 호스팅에 올리거나, 이 폴더에서 `python3 -m http.server`로 열어 확인하세요.

data/schools.json 구조
{ "version":1, "updatedAt":"YYYY-MM-DD",
  "schools":[ {id,name,kind,region,address,coedu,website,status,dates,checked,lat,lon}, ... ],
  "rawEvents":{ 학교id:{ "YYYYMMDD":["행사명",...] } },
  "reviewDates":{ 학교id:["YYYYMMDD",...] } }

[자동 갱신]
scripts/update_schools.py : 나이스 학사일정을 조회해 data/schools.json 갱신 (키는 환경변수 NEIS_KEY)
scripts/test_classify.py  : 분류 규칙 테스트
.github/workflows/update-data.yml : GitHub에 올렸을 때 매주 자동 실행 (Secrets에 NEIS_KEY 등록)
처음 한 번 (인터넷·키 없이 가능): 기존 수집 결과와 분류가 같은지 대조
  python3 scripts/verify_against_audit.py school_summary.csv event_audit.csv   → 불일치 0곳이면 정상
scripts/update_schools.py --refresh-directory : 신설 학교 추가, 주소·홈페이지 갱신 (한 달에 한 번)
