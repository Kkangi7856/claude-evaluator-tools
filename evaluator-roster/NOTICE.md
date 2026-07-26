# evaluator-roster

선정·단계 평가위원/후보자 명단을 병합하여 **최종평가위원 섭외우선(안)** 을 자동 작성하는 플러그인.

## 구성
```
evaluator-roster/
├── .claude-plugin/
│   └── plugin.json                 # 플러그인 메타데이터
├── commands/
│   └── build-shortlist.md          # /evaluator-roster:build-shortlist 명령어
├── agents/
│   └── shortlist.md                # 하위호환 wrapper 에이전트
├── skills/
│   └── committee-shortlist/
│       ├── SKILL.md                # 병합 로직·열 매핑·판정 규칙 명세
│       └── scripts/
│           └── build_shortlist.py  # 실제 병합 스크립트 (openpyxl)
└── NOTICE.md
```

## 사용
```
/evaluator-roster:build-shortlist
```
또는 직접 실행:
```
python skills/committee-shortlist/scripts/build_shortlist.py \
  --seon "선정평가위원 및 후보자 명단.xlsx" \
  --dan  "단계평가위원 및 후보자 명단.xlsx" \
  --template "최종평가위원 섭외우선(안).xlsx" \
  --out "최종평가위원 섭외우선(안)_결과.xlsx"
```

## 기능
- 두 명단의 **C~K열**(성명·소속·부서·직위·국가연구자번호·전공·기술분류1~3)을 가져와 취합
- **W열(참석여부)** `Y` = 실제 참여 위원 / 공란 = 후보자
- **K열(국가연구자번호)** 고유키로 중복 제거 → 1인 1행
- **B열(기평가 섭외이력)** 자동 산출 (선정평가위원 / 단계평가위원 / 후보자 / 선정·단계 결합)
- 섭외우선순위(위원 → 후보자)로 정렬

자세한 판정 규칙은 `skills/committee-shortlist/SKILL.md` 참고.

## 의존성
- Python 3
- `openpyxl` (`pip install openpyxl`)

## 라이선스
MIT
