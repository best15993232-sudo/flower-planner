# 데이터 구조: 장소와 행사

2026-10-29 전환. 학교 한 곳에 졸업식 하나만 붙던 구조를 **장소**와 **행사**로 나눴어요.
그래서 한 장소에 졸업식·입학식·공연·전시처럼 여러 행사를 붙일 수 있고, 공연장·전시장도 같은 방식으로 넣을 수 있어요.

## 파일
| 파일 | 누가 만드나 | 사이트가 읽나 | 내용 |
|---|---|---|---|
| `data/places.json` | `build_events.py` | O | 장소 (학교·대학 캠퍼스·나중에 공연장/전시장) |
| `data/events.json` | `build_events.py` | O | 행사 (지금은 2026학년도 졸업식·학위수여식) |
| `data/schools.json` | `update_schools.py` (매일) | X | 나이스 수집 작업 파일 |
| `data/universities.json` · `university_sources.json` | 대학 스크립트 · 사람 확인 | X | 대학 목록과 확인된 날짜 |
| `data/place_sizes.json` | `build_place_sizes.py` (1년에 1번) | X | 학교알리미 학생 수 |

수집 스크립트는 지금처럼 작업 파일을 고치고, 마지막에 `build_events.py`가 사이트용 두 파일을 다시 만들어요(매일 자동 실행에 포함).

## 장소 (places.json)
```json
{"id":"J10:7631265","type":"school","name":"동삭중학교","kind":"중학교","region":"경기",
 "address":"경기도 평택시 …","gender":"co","website":"…","lat":37.01,"lon":127.10,
 "size":{"students":946,"grads":327}}
```
- `type`: `school` 초중고 · `campus` 대학 캠퍼스 · `venue` 공연장/전시장/행사장(예정)
- `gender`: `co` 남녀공학 · `m` 남학교 · `f` 여학교 (대학은 여자대학만 `f`)
- `size`: 규모. 학교는 `students` 전체 학생 수, `grads` 졸업 학년 학생 수. 공연장·전시장은 `seats` 좌석 수, `area` 면적(㎡)을 넣어요. 모르면 빠져요.
- 파일 위에 `sizeYear`(학생 수 기준 연도), `sizeSource`(출처)가 있어요.

## 행사 (events.json)
```json
{"id":"grad:J10:7631265:2026","place":"J10:7631265","type":"graduation","term":"2026",
 "label":"졸업식","status":"registered","date":"20270108",
 "source":{"kind":"neis","checked":"2026-10-29"},"winterStart":"20270108",
 "history":[{"from":["20270115"],"at":"2026-11-20"}]}
```
- `id`: `종류:장소id:학년도`. 사용자가 담은 일정은 이 id(`eventId`)로 행사와 이어져요.
- `type`: `graduation` 졸업식·학위수여식 (나중에 `entrance`, `concert`, `exhibition` 등)
- `unit`: 행사 단위. 대학은 `학부`(단과대·대학원은 따로 붙일 수 있어요)
- `status` 확인 단계
  | 값 | 뜻 | 화면 |
  |---|---|---|
  | `registered` | 나이스에 졸업식 하루 등록 | 나이스 일정 등록 |
  | `confirmed` | 운영자가 학교 학사일정 원문에서 확인 | 학교 일정 확인 |
  | `review_multiple` | 후보 날짜 여러 개 (`candidates`) | 날짜 후보 여러 개 |
  | `review_name` | 행사명이 애매 (`candidates`, `rawNames`) | 행사명 확인 필요 |
  | `missing` | 아직 등록 안 됨 | 졸업일 미등록 / 직접 입력 |
  | `no_data` | 학사일정 자료 없음 | 학사일정 자료 없음 |
  | `not_queried` | 아직 조회 전 | 아직 조회 전 |
- `date`는 `registered`·`confirmed`일 때만 있어요. 나머지는 `null`.
- `source`: `kind`(neis · school_page · none), `url`, `checked`(확인일)
- `history`: 날짜가 바뀐 기록. 날짜 변경 알림에 써요.

## 저장된 내 일정 (사용자 기기)
`{id, schoolId, eventId, type, date, source, note, qty, ack, savedAt}`
- `schoolId`는 장소 id예요(이름은 예전 그대로 둬요).
- 예전에 담은 일정은 사이트를 열 때 자동으로 `eventId`가 붙어요. 백업 파일도 그대로 불러와져요.

## 학생 수 갱신 (1년에 1번, 4~6월 공시 뒤)
1. 학교알리미 > 공개용데이터에서 시도교육청 **전체**로 받기
   - 학교기본정보: 학교급별 (초·중·고·특수·그외·각종)
   - 학사/학생 > **학년별·학급별 학생수**: 공시년도 올해, 학교급별
2. `python3 scripts/build_place_sizes.py --year 2027 --info 기본정보폴더 --students 학생수폴더`
3. `python3 scripts/build_events.py` 후 커밋
- 학교알리미 코드(S0…)는 나이스 코드와 달라서 **이름 + 좌표 3km 이내**로 이어요. 2026년 기준 12,060곳 중 11,971곳(99.3%)이 이어졌어요. 못 이은 목록은 `docs/reports/place_sizes_unmatched_연도.txt`.
- 같은 학교에 두 줄이 붙으면 둘 다 비워요. 잘못된 숫자를 보여주는 것보다 안 보여주는 게 나아서요.
