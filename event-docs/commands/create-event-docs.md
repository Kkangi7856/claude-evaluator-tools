---
name: create-event-docs
description: 행사 개요(웹주소 또는 파일)로 「행사 개최 계획(안)」과 「공문(보고+요청)」을 한글(.hwp)로 생성합니다.
argument-hint: "<행사 웹주소 URL 또는 행사 개요 파일 경로>"
---

# 행사 개최 계획(안) + 공문 생성

`event-docs` 스킬을 사용해 행사 문서 2종을 작성한다.

## 입력
`$ARGUMENTS` 로 전달된 **웹주소(URL)** 또는 **파일 경로**에서 행사 개요를 가져온다.
입력이 없으면 사용자에게 URL 또는 파일을 요청한다.

## 절차
1. **행사 정보 수집** — URL이면 `WebFetch`, 파일이면 파일을 읽어 행사명·일시·장소·
   주최/주관·참가대상·목적·프로그램·세부일정·문의처 등을 추출한다.
   핵심 항목(행사명/일시/장소)이 없으면 사용자에게 확인하고, 없는 정보는 지어내지 않는다.
2. **스펙 작성** — `event-docs` 스킬의 `SKILL.md` 스키마에 맞춰 `event_spec.json` 을 작성한다.
3. **의존성 확인** — `pyhwpx`, `pandas` 미설치 시 `pip install pyhwpx pandas` (한컴오피스 필요).
4. **생성 스크립트 실행**
   ```
   python "${CLAUDE_PLUGIN_ROOT}/skills/event-docs/scripts/render_docs.py" --spec "event_spec.json" --template "${CLAUDE_PLUGIN_ROOT}/skills/event-docs/assets/gongmun_template.hwp" --outdir "."
   ```
5. **결과 보고** — 생성된 `<행사명> 개최 계획(안).hwp`, `<행사명> 공문.hwp` 경로와
   주요 내용을 표로 요약한다.

## 산출물
- 「행사 개최 계획(안)」 — 개요·목적·프로그램·일정·소요예산(빈 양식)·기대효과·행정사항
- 「공문」 2종 — 개최 계획(안) 보고(내부) + 참석 요청(외부, 참석자 명단 빈 표·붙임)
