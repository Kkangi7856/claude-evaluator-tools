# evaluation-summary

평가위원 답변 엑셀을 읽어 **항목별로 중복 없이 평가의견을 정리**하고
「평가의견 종합」을 한글(.hwp)로 자동 생성하는 플러그인.

## 구성
```
evaluation-summary/
├── .claude-plugin/
│   └── plugin.json                       # 플러그인 메타데이터
├── commands/
│   └── summarize-evaluations.md          # /evaluation-summary:summarize-evaluations 명령어
├── agents/
│   └── evaluation-summary.md             # 하위호환 wrapper 에이전트
├── skills/
│   └── evaluation-summary/
│       ├── SKILL.md                      # 추출→항목별 중복제거→생성 절차·스키마
│       └── scripts/
│           └── render_summary.py         # 엑셀 추출(--extract) / .hwp 생성(--spec)
├── references/
│   └── sample-spec.json                  # 정리 스펙 JSON 예시
└── NOTICE.md
```

## 사용
```
/evaluation-summary:summarize-evaluations <평가표 답변 목록 엑셀 경로>
```
또는 자연어로 "이 평가표 답변 엑셀을 항목별로 정리해서 한글로 만들어줘" 요청.

## 입력 엑셀 구성(기본)
| 열 | 내용 |
|---|---|
| A | 평가위원명 |
| C | 우수한 점 |
| D | 수정 및 보완할 점 |
| E | 기타 의견 |

열 위치가 다르면 `--name-col/--good-col/--fix-col/--etc-col` 로 지정한다.

## 산출물
- **평가의견 종합.hwp** — `1. 우수한 점`, `2. 수정 및 보완할 점`, `3. 기타 의견` 아래에
  여러 평가위원의 의견을 **중복 없이** `ㅇ ~~` 형식으로 정리(평가위원 이름 미표기).

## 동작 원리
- `--extract` 로 엑셀에서 평가위원별 원문 의견을 추출 → **Claude 가 항목별로 의미 기준 중복 제거·정리**
  → `summary_spec.json` 작성 → `render_summary.py --spec` 이 한컴오피스 COM 자동화로 네이티브 `.hwp` 생성.

## 의존성
- **한컴오피스(HWP)** 설치 필요(네이티브 .hwp 생성)
- Python: `pyhwpx`, `openpyxl`

## 라이선스
MIT
