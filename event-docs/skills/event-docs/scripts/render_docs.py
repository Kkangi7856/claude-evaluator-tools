# -*- coding: utf-8 -*-
"""
render_docs.py — 행사 개요(JSON) → 「개최 계획(안)」 + 「공문(보고+요청)」 .hwp 생성

- 공문: 워크숍 공문 서식(gongmun_template.hwp)을 열어 누름틀 필드 채우기 + 정밀 치환.
- 개최 계획(안): pyhwpx로 신규 생성(공공기관 표준 양식).

사용:
  python render_docs.py --spec event.json --template gongmun_template.hwp --outdir .
JSON 스펙 예시는 references/sample-spec.json 참조.
"""
import argparse, json, os, shutil, sys
from pyhwpx import Hwp

GRAY = (217, 217, 217)


# ---------- 유틸 ----------
def has_final_consonant(word):
    """마지막 글자에 받침이 있으면 True (조사 을/를 판단용)"""
    w = (word or "").strip()
    if not w:
        return False
    ch = w[-1]
    if '가' <= ch <= '힣':
        return (ord(ch) - 0xAC00) % 28 != 0
    # 숫자/영문 등은 받침 없다고 간주
    return False


def eul_reul(word):
    return "을" if has_final_consonant(word) else "를"


def as_lines(v):
    """문자열/리스트를 라인 리스트로."""
    if v is None:
        return []
    if isinstance(v, (list, tuple)):
        return [str(x) for x in v if str(x).strip()]
    return [str(v)]


# ---------- 개최 계획(안) 신규 생성 ----------
def write_para(hwp, text="", bold=False, size=11, align="left", indent_spaces=0):
    if align == "center":
        hwp.ParagraphShapeAlignCenter()
    else:
        hwp.ParagraphShapeAlignLeft()
    if bold or size:
        hwp.set_font(Bold=bold, Height=size)
    if indent_spaces:
        text = (" " * indent_spaces) + text
    hwp.insert_text(text)
    hwp.BreakPara()


def insert_table_at_marker(hwp, marker, columns, rows):
    """문서 내 marker 텍스트 위치에 표를 삽입(표-캐럿 문제 회피용).
    본문 텍스트를 모두 작성한 뒤 호출한다."""
    import pandas as pd
    hwp.MoveDocBegin()
    if not hwp.find_forward(marker):
        return
    # find_forward는 찾은 문자열을 선택상태로 둠 -> 삭제 후 그 자리에 표 삽입
    hwp.HAction.Run("Delete")
    df = pd.DataFrame(rows, columns=columns)
    hwp.table_from_data(df, index=False, header=True, cell_fill=GRAY, header_bold=True)


def build_plan(hwp, spec, outpath):
    ev = spec.get("event_name", "")
    hwp.set_font(FaceName="함초롬바탕", Height=11)

    SCHED_MARK = "@@SCHEDULE_TABLE@@"
    BUDGET_MARK = "@@BUDGET_TABLE@@"

    # ===== 1) 본문 텍스트 먼저 작성(표 자리는 마커) =====
    write_para(hwp, f"「{ev}」 개최 계획(안)", bold=True, size=16, align="center")
    write_para(hwp, "", size=11)

    write_para(hwp, "□ 1. 행사 개요", bold=True, size=12)
    overview = [
        ("행 사 명", ev),
        ("일    시", spec.get("datetime", "")),
        ("장    소", spec.get("venue", "")),
        ("주최/주관", spec.get("host", "")),
        ("참가대상", spec.get("target", "")),
        ("규    모", spec.get("scale", "")),
    ]
    for k, v in overview:
        if str(v).strip():
            write_para(hwp, f"○ {k} : {v}", size=11, indent_spaces=2)
    write_para(hwp, "", size=11)

    write_para(hwp, "□ 2. 개최 목적", bold=True, size=12)
    for line in as_lines(spec.get("purpose")):
        write_para(hwp, f"○ {line}", size=11, indent_spaces=2)
    write_para(hwp, "", size=11)

    progs = as_lines(spec.get("programs"))
    if progs:
        write_para(hwp, "□ 3. 주요 프로그램", bold=True, size=12)
        for p in progs:
            write_para(hwp, f"○ {p}", size=11, indent_spaces=2)
        write_para(hwp, "", size=11)

    sched = spec.get("schedule") or []
    if sched:
        write_para(hwp, "□ 4. 세부 일정", bold=True, size=12)
        write_para(hwp, SCHED_MARK, size=11)
        write_para(hwp, "", size=11)

    write_para(hwp, "□ 5. 소요예산(안)", bold=True, size=12)
    write_para(hwp, BUDGET_MARK, size=11)
    write_para(hwp, "  ※ 세부 금액은 확정 후 기재", size=10, indent_spaces=2)
    write_para(hwp, "", size=11)

    effects = as_lines(spec.get("effects"))
    if effects:
        write_para(hwp, "□ 6. 기대효과", bold=True, size=12)
        for e in effects:
            write_para(hwp, f"○ {e}", size=11, indent_spaces=2)
        write_para(hwp, "", size=11)

    write_para(hwp, "□ 7. 행정사항", bold=True, size=12)
    for line in as_lines(spec.get("admin")):
        write_para(hwp, f"○ {line}", size=11, indent_spaces=2)
    if spec.get("contact"):
        write_para(hwp, f"○ 문의처 : {spec['contact']}", size=11, indent_spaces=2)

    # ===== 2) 마커 자리에 표 삽입 =====
    if sched:
        rows = [[s.get("division", ""), s.get("date", ""), s.get("content", "")] for s in sched]
        insert_table_at_marker(hwp, SCHED_MARK, ["구 분", "일 자", "내 용"], rows)

    budget_rows = spec.get("budget_rows") or ["행사 운영비", "회의 및 행사개최비", "홍보비", "임차료"]
    b_rows = [[c, "", ""] for c in budget_rows] + [["합    계", "", ""]]
    insert_table_at_marker(hwp, BUDGET_MARK, ["구 분", "금 액", "산출내역"], b_rows)

    hwp.MoveDocEnd()
    hwp.save_as(outpath, "HWP")
    try:
        hwp.save_as(outpath[:-4] + ".pdf", "PDF")
    except Exception:
        pass


# ---------- 공문(보고 + 요청) 생성 ----------
def find_table_index(hwp, first_cell_startswith):
    for ti in range(6):
        try:
            hwp.get_into_nth_table(ti)
        except Exception:
            break
        hwp.TableCellBlock()
        t = hwp.get_selected_text() or ""
        hwp.Cancel()
        if t.strip().startswith(first_cell_startswith):
            return ti
    return None


def clear_table_cells(hwp, table_idx, keep):
    """keep(col_letter, row_int)->True면 유지. 나머지 셀 텍스트 삭제."""
    hwp.get_into_nth_table(table_idx)
    visited = set()
    for _ in range(200):
        a = hwp.get_cell_addr()
        if not a or a in visited:
            break
        visited.add(a)
        col = a[0]
        try:
            row = int(a[1:])
        except ValueError:
            row = 0
        if not keep(col, row):
            hwp.MoveListBegin()
            hwp.MoveSelListEnd()
            hwp.HAction.Run("Delete")
        hwp.TableRightCell()


def set_table_cells(hwp, table_idx, values):
    """values: {셀주소('B2') -> 텍스트}. 해당 셀에 텍스트 기입."""
    hwp.get_into_nth_table(table_idx)
    visited = set()
    for _ in range(800):
        a = hwp.get_cell_addr()
        if not a or a in visited:
            break
        visited.add(a)
        if a in values:
            hwp.MoveListBegin()
            hwp.MoveSelListEnd()
            hwp.HAction.Run("Delete")
            hwp.insert_text(str(values[a]))
        hwp.TableRightCell()


def fill_attendee_table(hwp, table_idx, attendees, base_data_rows=15):
    """참석자 명단표(순번/성명/소속/직위)에 초청자 자동 기입.
    attendees: [{name, org, title}, ...]. base_data_rows 초과 시 행 자동 추가."""
    n = len(attendees)

    def goto_last_cell():
        hwp.get_into_nth_table(table_idx)
        prev = None
        for _ in range(800):
            a = hwp.get_cell_addr()
            if a == prev:
                break
            prev = a
            hwp.TableRightCell()

    if n > base_data_rows:
        # 필요한 만큼 행 추가 (매번 마지막 셀로 이동 후 추가해야 정상 추가됨)
        for _ in range(n - base_data_rows):
            goto_last_cell()
            hwp.TableRightCellAppend()

    values = {}
    for i, att in enumerate(attendees):
        row = 2 + i  # 1행=헤더, 데이터는 2행부터
        values[f"B{row}"] = att.get("name", "")
        values[f"C{row}"] = att.get("org", "")
        values[f"D{row}"] = att.get("title", "")
        if row > base_data_rows + 1:  # 추가된 행은 순번도 기입
            values[f"A{row}"] = str(i + 1)
    set_table_cells(hwp, table_idx, values)


def build_gongmun(hwp, spec, template, outpath):
    ev = spec.get("event_name", "")
    ww = spec.get("datetime_venue") or f"{spec.get('datetime','')} / {spec.get('venue','')}"
    purpose = " / ".join(as_lines(spec.get("purpose")))
    report_att = spec.get("report_attendees", spec.get("target", ""))
    target = spec.get("target", "")
    note = spec.get("gongmun_note", "세부 프로그램 및 참가등록은 붙임 및 홈페이지 참조")
    budget_total = spec.get("budget_total", "")

    work = outpath + ".tmp.hwp"
    shutil.copy(template, work)
    hwp.open(work)

    # 1) 보고 공문 본문(plain text) 정밀 치환 — SeveralWords=0
    def R(a, b):
        hwp.find_replace_all(a, b, SeveralWords=0)

    # (보고 공문) 본문 정밀 치환
    R("위 호 관련, 2026년도 OO 워크숍을 다음과 같이 개최하고자 합니다.",
      f"「{ev}」 개최 계획을 다음과 같이 보고합니다.")
    R("2026.6.4.(목) 10:00 ~ 16:15 / 비즈허브 서울센터 202호", ww)
    R("신규기획 주제 요약문 중에서 실제 신규과제화 가능성이 높은 주제 선정", purpose)
    R("부처, 외부 전문가, 유관기관, 자문위원 등 24인 내외", report_att)
    R("라. 소요예산(안): 7,290,000원",
      f"라. 소요예산(안): {budget_total or '붙임 「개최 계획(안)」 참조'}")

    # (참석요청 공문) 본문_2 필드 내 텍스트 정밀 치환 — 참석자 명단표는 보존
    R("2026년도 OO 워크숍을 아래와 같이 개최하고자 하오니",
      f"「{ev}」{eul_reul(ev)} 아래와 같이 개최하고자 하오니")
    R("가. 회의명: 2026년도 OO 워크숍", f"가. 회의명: {ev}")
    R("다. 참석 대상: 유관기관 전문가 총 15인", f"다. 참석 대상: {target}")
    R("전문가수당 200,000원 지급 예정", note)
    R("2026년도 OO 워크숍 추진계획(안) 1부.", f"「{ev}」 개최 계획(안) 1부.")

    # 2) 예산표 빈 양식화(구분/헤더 유지, 금액·산출내역 비움)
    bi = find_table_index(hwp, "구")
    if bi is not None:
        clear_table_cells(hwp, bi, keep=lambda c, r: c == "A" or r == 1)

    # 3) 참석자표: 예시행 비우기 후, 초청자 명단이 있으면 자동 채우기
    ai = find_table_index(hwp, "순번")
    if ai is not None:
        clear_table_cells(hwp, ai, keep=lambda c, r: c == "A" or r == 1)
        attendees = spec.get("attendees") or []
        if attendees:
            fill_attendee_table(hwp, ai, attendees)

    # 4) 제목 필드 채우기
    hwp.put_field_text("결재제목", f"{ev} 개최 계획(안) 보고")
    hwp.put_field_text("결재제목_2", f"{ev} 참석 요청")

    hwp.save_as(outpath, "HWP")
    try:
        hwp.save_as(outpath[:-4] + ".pdf", "PDF")
    except Exception:
        pass
    hwp.clear()
    try:
        os.remove(work)
    except OSError:
        pass


def safe_name(s):
    for ch in '\\/:*?"<>|':
        s = s.replace(ch, "")
    return s.strip()


def main(argv=None):
    ap = argparse.ArgumentParser(description="행사 개요(JSON) → 개최 계획(안) + 공문 .hwp 생성")
    ap.add_argument("--spec", required=True, help="행사 개요 JSON 파일")
    ap.add_argument("--template", required=True, help="공문 서식(gongmun_template.hwp)")
    ap.add_argument("--outdir", default=".", help="출력 폴더")
    a = ap.parse_args(argv)

    with open(a.spec, encoding="utf-8") as f:
        spec = json.load(f)
    ev = safe_name(spec.get("event_name", "행사"))
    os.makedirs(a.outdir, exist_ok=True)
    plan_path = os.path.join(a.outdir, f"{ev} 개최 계획(안).hwp")
    gong_path = os.path.join(a.outdir, f"{ev} 공문.hwp")

    hwp = Hwp(visible=False, new=True)
    build_plan(hwp, spec, plan_path)   # 신규 문서(초기 빈 문서 사용)
    build_gongmun(hwp, spec, a.template, gong_path)
    hwp.quit()

    print(f"[완료] 개최 계획(안): {plan_path}")
    print(f"[완료] 공문(보고+요청): {gong_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
