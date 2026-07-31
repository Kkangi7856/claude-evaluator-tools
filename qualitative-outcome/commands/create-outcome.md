---
name: create-outcome
description: 보도자료(.hwp/.hwpx)를 「정성성과 양식」 항목대로 정리해 한글(.hwpx) 문서로 생성합니다.
argument-hint: "<보도자료 파일 경로> [정성성과 양식 파일 경로]"
---

# 보도자료 → 정성성과 정리

`qualitative-outcome` 스킬을 사용해 보도자료를 「정성성과 양식」의 6개 항목대로 정리한다.

## 입력
`$ARGUMENTS` 로 전달된 **보도자료 파일 경로**(.hwp/.hwpx/.txt/.md)를 사용한다.
입력이 없으면 사용자에게 보도자료 파일 경로를 요청한다.
두 번째 인자로 양식 파일(.hwpx)이 주어지면 `--template` 으로 넘긴다(없으면 번들 양식 사용).

## 절차
1. **보도자료 추출**
   ```
   python "${CLAUDE_PLUGIN_ROOT}/skills/qualitative-outcome/scripts/extract_press.py" "$ARGUMENTS" --images-dir "_press_images" --json "press.json"
   ```
   본문 텍스트, 삽입 이미지, URL 목록을 얻는다.
2. **항목별 재구성** — 추출된 본문**만**을 근거로 아래 6개 항목을 작성한다.
   `성과명` / `관련 사업 (과제)` / `추진배경` / `추진내용` / `추진성과` / `비고`
   - 계층: `□ 요지` → ` ○ 세부` → `   - 근거`, 명사형 종결
   - 문체·항목별 요령은 `references/writing-guide.md` 참조
3. **공란 처리** — 보도자료에 없는 정보는 **절대 지어내지 않고 비운다.**
   - 과제명·과제번호·수행기관/연구책임자·총 연구기간·총 연구비
   - 관련기사 제목·언론사·날짜·기사 링크
   - 그림(추출된 이미지가 없을 때)
4. **스펙 작성** — `qualitative-outcome` 스킬 `SKILL.md` 스키마에 맞춰 `outcome_spec.json` 작성.
   추출된 이미지가 있으면 `image.path` 와 보도자료의 그림 설명을 `image.caption` 으로 넣는다.
5. **의존성 확인** — `olefile`, `pillow` 미설치 시 `pip install olefile pillow`.
6. **문서 생성**
   ```
   python "${CLAUDE_PLUGIN_ROOT}/skills/qualitative-outcome/scripts/render_outcome.py" --spec "outcome_spec.json" --outdir "."
   ```
   `.hwp`/`.pdf` 도 필요하면 `--to-hwp` 추가(한컴오피스 필요).
7. **결과 보고** — 생성된 `정성성과.hwpx` 경로와 함께 **공란으로 남긴 항목을 목록으로 안내**한다.

## 산출물
- 「정성성과」 — 성과명·관련 사업(과제)·추진배경·추진내용·추진성과·비고 6개 칸이
  보도자료 사실 범위 내에서 채워진 한글(.hwpx) 문서 (그림 있으면 추진성과 칸에 삽입)
