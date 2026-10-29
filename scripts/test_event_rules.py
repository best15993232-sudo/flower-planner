"""행사명 분류 규칙 회귀 테스트.
실제로 나이스·학교 자료에서 본 행사명 중 헷갈리기 쉬운 것들을 모았어요.
규칙을 고칠 때마다 이 테스트가 통과해야 해요. 새로 발견한 오분류는 여기에 추가하세요."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from update_schools import event_class, classify, ST_OK, ST_MULTI, ST_AMBIG, ST_NONE

CASES = [
    # (행사명, 기대 분류, 어디서 봤는지)
    ("졸업식", "graduation", "대부분 학교"),
    ("제70회 졸업식", "graduation", "회차가 붙은 표기"),
    ("졸업식 및 종업식", "graduation", ""),
    ("졸업·종업식", "graduation", ""),
    ("졸업식, 겨울방학식", "graduation", "서울남천초 홈페이지 표기 (방학식은 휴업 아님)"),
    ("졸업식 휴업", "review", "신송중: 21일 연속 등록 → 졸업식 날짜로 단정 불가"),
    ("졸업식휴업일", "review", ""),
    ("졸업식 리허설", "excluded", "준비 행사"),
    ("졸업식 예행연습", "excluded", "준비 행사"),
    ("졸업식 준비", "excluded", ""),
    ("졸업앨범 촬영", "excluded", ""),
    ("졸업사정회", "excluded", "회의"),
    ("졸업 및 진급 사정회", "excluded", "웅천고 (이전에는 확인 필요로 잘못 분류)"),
    ("졸업후 미산입일", "excluded", ""),
    ("졸업연주회", "future_event", "음악 계열"),
    ("졸업작품전시회", "future_event", "미술 계열"),
    ("졸업식 연주회", "review", "공연과 섞임"),
    ("졸업장수여식", "review", "기산초: 졸업식 표기 아님"),
    ("졸업", "review", "신성고: 너무 짧음"),
    ("종업식", "other", ""),
    ("겨울방학", "other", ""),
]

bad = 0
for name, want, where in CASES:
    got = event_class(name)
    ok = got == want; bad += not ok
    print("OK  " if ok else "FAIL", f"{name:<18} → {got:<13}" + ("" if ok else f" (기대: {want}) {where}"))

R = lambda d, n: {"AA_YMD": d, "EVENT_NM": n}
# 학교 단위 판정
school_cases = [
    ([R("20270208", "졸업식 휴업"), R("20270209", "졸업식 휴업")], ST_AMBIG, [], "졸업식 휴업만 있으면 확인 필요"),
    ([R("20270108", "졸업식"), R("20270108", "졸업식 휴업")], ST_OK, ["20270108"], "같은 날 졸업식이 있으면 등록"),
    ([R("20261231", "졸업식"), R("20270106", "졸업식")], ST_MULTI, ["20261231", "20270106"], "천안청수고형"),
    ([R("20261230", "졸업 및 진급 사정회")], ST_NONE, [], "웅천고형"),
]
for rows, st, dates, why in school_cases:
    s, d, *_ = classify(rows)
    ok = (s, d) == (st, dates); bad += not ok
    print("OK  " if ok else "FAIL", why, s, d)
print(f"\n{len(CASES)+len(school_cases)}개 중 실패 {bad}개")
sys.exit(1 if bad else 0)
