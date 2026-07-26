# event-docs

행사 개요(웹주소 또는 파일)를 입력하면 **「행사 개최 계획(안)」** 과 **「공문(개최 계획 보고 + 참석 요청)」** 을
한글(.hwp)로 자동 생성하는 플러그인.

## 구성
```
event-docs/
├── .claude-plugin/
│   └── plugin.json                     # 플러그인 메타데이터
├── commands/
│   └── create-event-docs.md            # /event-docs:create-event-docs 명령어
├── agents/
│   └── event-docs.md                   # 하위호환 wrapper 에이전트
├── skills/
│   └── event-docs/
│       ├── SKILL.md                    # 정보수집→스펙→생성 절차·스키마·구현 메모
│       ├── scripts/
│       │   └── render_docs.py          # .hwp 생성 스크립트 (pyhwpx)
│       ├── assets/
│       │   └── gongmun_template.hwp     # 공문 서식(워크숍 공문 기반)
│       └── references/
│           └── sample-spec.json         # 행사 스펙 JSON 예시(학술대회)
└── NOTICE.md
```

## 사용
```
/event-docs:create-event-docs <행사 웹주소 또는 파일 경로>
```
또는 자연어로 "이 행사 페이지로 개최 계획(안)과 공문 만들어줘 + URL/파일" 요청.

## 산출물
- **행사 개최 계획(안)** — 개요·목적·프로그램·세부일정(표)·소요예산(빈 표)·기대효과·행정사항
- **공문 2종** — (1면) 개최 계획(안) 보고 + 소요예산 빈 표 / (2면) 참석 요청 + 참석자 명단표 + 붙임

## 참석자 명단표 (선택)
스펙에 `attendees`(초청자 명단) 배열을 넣으면 참석 요청 공문의 명단표(순번·성명·소속·직위)가
자동으로 채워진다(순번 자동, 15명 초과 시 행 자동 추가). 생략 시 빈 양식(15행)으로 남는다.

## 동작 원리
- 행사 정보 추출은 Claude가 수행(URL은 WebFetch, 파일은 직접 읽기) → `event_spec.json` 작성.
- `render_docs.py` 가 한컴오피스 COM 자동화로 네이티브 `.hwp` 생성.
  - 공문: 서식 파일을 열어 누름틀 필드(제목) + 정밀 치환(본문, `SeveralWords=0`) + 표 빈 양식화.
  - 계획안: 신규 문서로 작성(마커 자리에 표 삽입).

## 의존성
- **한컴오피스(HWP)** 설치 필요 (네이티브 .hwp 생성)
- Python: `pyhwpx`, `pandas`, `openpyxl`

## 라이선스
MIT
