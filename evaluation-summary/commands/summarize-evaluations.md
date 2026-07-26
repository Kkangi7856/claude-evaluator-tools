---
name: summarize-evaluations
description: 평가위원 답변 엑셀을 항목별로 중복 없이 정리하여 「평가의견 종합」을 한글(.hwp)로 생성합니다.
argument-hint: "<평가표 답변 목록 엑셀 파일 경로>"
---

# 평가의견 종합 정리

`evaluation-summary` 스킬을 사용해 평가위원 답변 엑셀을 항목별로 정리한 한글 문서를 작성한다.

## 입력
`$ARGUMENTS` 로 전달된 **엑셀 파일 경로**(평가표 답변 목록)를 사용한다.
입력이 없으면 사용자에게 엑셀 파일 경로를 요청한다.
기본 열 구성: A열=평가위원명, C열=우수한 점, D열=수정 및 보완할 점, E열=기타 의견.

## 절차
1. **원문 추출**
   ```
   python "${CLAUDE_PLUGIN_ROOT}/skills/evaluation-summary/scripts/render_summary.py" --extract "$ARGUMENTS"
   ```
   (열이 다르면 `--name-col/--good-col/--fix-col/--etc-col` 로 지정)
2. **항목별 정리** — 세 항목(우수한 점 / 수정 및 보완할 점 / 기타 의견) 각각에 대해
   모든 평가위원의 의견을 모아 **의미가 겹치는 내용을 하나로 병합**하고, 서로 다른 논점을
   `ㅇ ~~` 형식으로 재작성한다. **평가위원 이름은 넣지 않는다.** 원문의 취지는 유지하되
   문장 형식은 자연스럽게 다듬어도 된다.
3. **스펙 작성** — `evaluation-summary` 스킬의 `SKILL.md` 스키마에 맞춰 `summary_spec.json` 을 작성한다.
4. **의존성 확인** — `pyhwpx`, `openpyxl` 미설치 시 `pip install pyhwpx openpyxl` (한컴오피스 필요).
5. **생성 스크립트 실행**
   ```
   python "${CLAUDE_PLUGIN_ROOT}/skills/evaluation-summary/scripts/render_summary.py" --spec "summary_spec.json" --outdir "."
   ```
6. **결과 보고** — 생성된 `평가의견 종합.hwp` 경로와 항목별 정리 개수를 표로 요약한다.

## 산출물
- 「평가의견 종합」 — `1. 우수한 점`, `2. 수정 및 보완할 점`, `3. 기타 의견` 아래에
  중복이 제거된 `ㅇ` 형식의 정리 의견이 항목별로 정리된 한글(.hwp) 문서
