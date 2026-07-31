# qualitative-outcome

보도자료(.hwp/.hwpx)를 읽어 **「정성성과 양식」의 6개 항목대로 성과를 정리**하고
한글(.hwpx, 선택적으로 .hwp/.pdf)로 자동 생성하는 플러그인.

## 구성
```
qualitative-outcome/
├── .claude-plugin/
│   └── plugin.json                        # 플러그인 메타데이터
├── commands/
│   └── create-outcome.md                  # /qualitative-outcome:create-outcome 명령어
├── agents/
│   └── qualitative-outcome.md             # 하위호환 wrapper 에이전트
├── skills/
│   └── qualitative-outcome/
│       ├── SKILL.md                       # 추출→항목별 작성→생성 절차·스키마
│       ├── assets/
│       │   └── outcome-template.hwpx      # 정성성과 양식(2열 6행 표)
│       └── scripts/
│           ├── extract_press.py           # 보도자료 텍스트·이미지·링크 추출
│           └── render_outcome.py          # 스펙(JSON) → 정성성과 한글 문서 생성
├── references/
│   ├── sample-spec.json                   # 스펙 JSON 예시
│   └── writing-guide.md                   # 항목별 작성 규칙·문체 가이드
└── NOTICE.md
```

## 사용
```
/qualitative-outcome:create-outcome <보도자료 파일 경로>
```
또는 자연어로 "이 보도자료로 정성성과 정리해줘" 요청.

## 출력 양식(2열 6행 표)
| 항목 | 내용 |
|---|---|
| 성과명9) | 보도자료 제목 + 부제 |
| 관련 사업 (과제) | 사업명 / 과제명 / 수행기관·연구책임자 / 연구기간 / 연구비 |
| 추진배경 | 연구가 필요했던 배경·문제의식 |
| 추진내용 | 실제 수행한 연구·개발 내용 |
| 추진성과 | 규명·확보한 결과, 게재 학술지, 기대효과 (+ 그림·캡션) |
| 비고 | 관련기사 제목(언론사, 날짜) 및 기사 링크 |

## 핵심 원칙 — 사실성
- **보도자료에 적힌 내용만으로 작성한다.** 허위사실·추정·외부 지식 삽입 금지.
- **사진, 보도자료 링크, 사업·과제 정보가 보도자료에 없으면 해당 줄은 공란으로 둔다.**
  (사용자가 직접 채워 넣음)
- 보도자료에 포함된 그림이 있으면 자동으로 추출해 「추진성과」 칸에 삽입한다.

## 산출물
- **정성성과.hwpx** — 양식 표의 각 칸이 채워진 한글 문서
- (`--to-hwp` 지정 시) **정성성과.hwp** / **정성성과.pdf**

## 동작 원리
`extract_press.py` 가 보도자료 원문·삽입 이미지·URL 을 추출 →
**Claude 가 양식 항목별로 재구성(사실 범위 내)** → `outcome_spec.json` 작성 →
`render_outcome.py` 가 양식 hwpx 템플릿의 표 칸을 채워 네이티브 한글 문서를 생성.

## 의존성
- Python 3.8+ (표준 라이브러리만으로 .hwpx 생성 가능)
- `olefile` — 바이너리 `.hwp` 보도자료 읽기 (`pip install olefile`)
- `pillow` — 이미지 크기 산출 (`pip install pillow`) *(없으면 기본 크기로 삽입)*
- `pyhwpx` + 한컴오피스 — `--to-hwp` 로 `.hwp`/`.pdf` 도 만들 때만 필요

## 라이선스
MIT
