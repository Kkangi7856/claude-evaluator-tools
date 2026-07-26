# evaluator-tools

업무 문서 자동화를 위한 Claude Code 플러그인 마켓플레이스입니다. 평가위원 명단 취합, 행사 개최 문서·공문 작성, 평가의견 종합 등 반복적인 공공/학술 행정 업무를 자동화하는 3개의 플러그인을 제공합니다.

## 설치

Claude Code에서 아래 명령으로 마켓플레이스를 추가합니다.

```
/plugin marketplace add kbo71928277/claude-evaluator-tools
```

그런 다음 원하는 플러그인을 설치합니다.

```
/plugin install evaluator-roster@evaluator-tools
/plugin install event-docs@evaluator-tools
/plugin install evaluation-summary@evaluator-tools
```

## 포함된 플러그인

| 플러그인 | 설명 |
|----------|------|
| **evaluator-roster** | 선정·단계 평가위원/후보자 명단을 병합하여 「최종평가위원 섭외우선(안)」을 자동 작성 |
| **event-docs** | 행사 개요(URL·파일)로 「행사 개최 계획(안)」과 「공문(보고+요청)」을 한글(.hwp)로 생성 |
| **evaluation-summary** | 평가위원 답변 엑셀을 항목(우수한 점·수정 및 보완할 점·기타 의견)별로 중복 없이 정리하여 「평가의견 종합」을 한글(.hwp)로 생성 |

## 구조

```
.claude-plugin/marketplace.json   # 마켓플레이스 정의
evaluator-roster/                 # 플러그인 1
event-docs/                       # 플러그인 2
evaluation-summary/               # 플러그인 3
```

각 플러그인 폴더의 `NOTICE.md`에서 상세 사용법을 확인할 수 있습니다.
