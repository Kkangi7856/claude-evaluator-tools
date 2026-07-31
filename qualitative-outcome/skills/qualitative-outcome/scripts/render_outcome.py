#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""정성성과 스펙(JSON)을 「정성성과 양식」 한글 문서(.hwpx)로 렌더링한다.

사용법
------
  python render_outcome.py --spec outcome_spec.json --outdir .
  python render_outcome.py --spec outcome_spec.json --to-hwp      # .hwp/.pdf 도 생성(한컴오피스 필요)
  python render_outcome.py --dump-template                        # 양식 표 구조 확인

스펙(JSON)
----------
  {
    "out_name": "정성성과.hwpx",
    "fields": {
      "성과명":            ["제목", "- 부제 -"],
      "관련 사업 (과제)":  ["□ 사업명: ...", "○ 과제명: ...", "  - 총 연구기간: "],
      "추진배경":          ["□ ...", " ○ ...", "   - ..."],
      "추진내용":          [...],
      "추진성과":          [...],
      "비고":              [...]
    },
    "image": { "path": "press_image1.bmp", "caption": "< 그림 설명 >" }
  }

- `fields` 의 각 값은 **문자열 배열**(한 줄 = 한 문단) 또는 개행이 포함된 문자열.
- 빈 배열 / 빈 문자열이면 해당 칸은 **공란**으로 남는다(내용을 지어내지 않기 위함).
- `image` 는 선택. 지정하면 「추진성과」 칸 끝에 그림 + 캡션이 삽입된다.
- 줄머리 기호(□ ○ ㅇ - ※ * ➔ …)는 자동으로 내어쓰기(행갈이 정렬)가 적용된다.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import sys
import unicodedata
import zipfile
import xml.etree.ElementTree as ET

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEMPLATE = os.path.join(HERE, "..", "assets", "outcome-template.hwpx")

NS = {
    "ha": "http://www.hancom.co.kr/hwpml/2011/app",
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hp10": "http://www.hancom.co.kr/hwpml/2016/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
    "hhs": "http://www.hancom.co.kr/hwpml/2011/history",
    "hm": "http://www.hancom.co.kr/hwpml/2011/master-page",
    "hpf": "http://www.hancom.co.kr/schema/2011/hpf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "opf": "http://www.idpf.org/2007/opf/",
    "ooxmlchart": "http://www.hancom.co.kr/hwpml/2016/ooxmlchart",
    "hwpunitchar": "http://www.hancom.co.kr/hwpml/2016/HwpUnitChar",
    "epub": "http://www.idpf.org/2007/ops",
    "config": "urn:oasis:names:tc:opendocument:xmlns:config:1.0",
}
for _p, _u in NS.items():
    ET.register_namespace(_p, _u)

XML_DECL = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'

# 양식 표의 행 순서(라벨 열 기준). 스펙 키는 이 라벨과 매칭된다.
ROW_LABELS = ["성과명", "관련 사업 (과제)", "추진배경", "추진내용", "추진성과", "비고"]

# 라벨 표기 흔들림 흡수용 별칭
ALIASES = {
    "성과명": {"성과명", "성과명9)", "성과 명", "제목"},
    "관련 사업 (과제)": {"관련 사업 (과제)", "관련사업(과제)", "관련 사업(과제)",
                     "관련사업 (과제)", "관련 사업", "사업(과제)"},
    "추진배경": {"추진배경", "추진 배경", "배경"},
    "추진내용": {"추진내용", "추진 내용", "내용"},
    "추진성과": {"추진성과", "추진 성과", "성과"},
    "비고": {"비고", "참고", "관련기사"},
}

# 줄머리 기호 — 이 기호로 시작하면 내어쓰기 폭을 자동 계산한다.
BULLETS = "□○●ㅇ◦◇◈▪▫·-–—*※➔→⇒>"

PX_TO_HWPUNIT = 75  # 96dpi 기준: 7200 / 96


def q(prefix: str, tag: str) -> str:
    return "{%s}%s" % (NS[prefix], tag)


# --------------------------------------------------------------- 유틸

def char_width(ch: str, em: int) -> int:
    """문자 하나의 대략적인 가로폭(HWPUNIT)."""
    if ch in ("\t",):
        return em * 2
    w = unicodedata.east_asian_width(ch)
    # 'A'(ambiguous)는 한글 문서에서 전각으로 조판된다(□, ○, ※ 등).
    return em if w in ("W", "F", "A") else em // 2


def hanging_indent(line: str, em: int) -> int:
    """줄머리(공백 + 기호 + 뒤따르는 공백)의 폭을 계산해 내어쓰기 값으로 쓴다."""
    m = re.match(r"^([\s ]*)([%s]|\d+[).]|[가-힣][).])(\s*)" % re.escape(BULLETS), line)
    if not m:
        # 기호가 없어도 선행 공백만큼은 맞춰 준다.
        lead = re.match(r"^[\s ]+", line)
        return sum(char_width(c, em) for c in lead.group(0)) if lead else 0
    prefix = m.group(0)
    if not m.group(3):  # 기호 뒤에 공백이 없으면 한 칸 있는 것으로 간주
        prefix += " "
    return sum(char_width(c, em) for c in prefix)


def as_lines(value) -> list:
    if value is None:
        return []
    if isinstance(value, str):
        lines = value.split("\n")
    elif isinstance(value, (list, tuple)):
        lines = []
        for v in value:
            lines.extend(str(v).split("\n"))
    else:
        lines = [str(value)]
    # 뒤쪽 빈 줄만 정리(중간 빈 줄은 의도된 것으로 본다)
    while lines and not lines[-1].strip():
        lines.pop()
    return [l.rstrip() for l in lines]


def normalize_fields(spec: dict) -> dict:
    raw = spec.get("fields") or {k: v for k, v in spec.items()
                                  if k not in ("out_name", "image", "title", "fields")}
    out = {}
    for label in ROW_LABELS:
        found = None
        for key, val in raw.items():
            norm = re.sub(r"\s+", "", str(key))
            if any(re.sub(r"\s+", "", a) == norm for a in ALIASES[label]):
                found = val
                break
        out[label] = as_lines(found)
    return out


# ------------------------------------------------------ header.xml 조작

class ParaPrFactory:
    """기존 paraPr 를 복제해 내어쓰기(intent)만 바꾼 paraPr 를 만들어 준다."""

    def __init__(self, header_xml: str):
        self.xml = header_xml
        ids = [int(i) for i in re.findall(r'<hh:paraPr id="(\d+)"', header_xml)]
        self.next_id = (max(ids) + 1) if ids else 0
        self.cache = {}
        self._blocks = {}
        for m in re.finditer(r'<hh:paraPr id="(\d+)".*?</hh:paraPr>', header_xml, re.S):
            self._blocks[m.group(1)] = m.group(0)
        self._new_blocks = []

    def base_indent(self, base_id: str) -> int:
        block = self._blocks.get(str(base_id), "")
        m = re.search(r'<hc:intent value="(-?\d+)"', block)
        return int(m.group(1)) if m else 0

    def base_align(self, base_id: str) -> str:
        block = self._blocks.get(str(base_id), "")
        m = re.search(r'<hh:align horizontal="(\w+)"', block)
        return m.group(1) if m else ""

    def get(self, base_id: str, indent: int, align: str | None = None) -> str:
        """intent = -indent (필요 시 정렬도 지정)인 paraPr id 를 돌려준다."""
        base_id = str(base_id)
        if indent == -self.base_indent(base_id) and (
                align is None or align == self.base_align(base_id)):
            return base_id
        key = (base_id, indent, align)
        if key in self.cache:
            return self.cache[key]
        block = self._blocks.get(base_id)
        if block is None:
            return base_id
        new_id = str(self.next_id)
        self.next_id += 1
        new_block = block.replace('<hh:paraPr id="%s"' % base_id,
                                  '<hh:paraPr id="%s"' % new_id, 1)
        # hp:case(HWPUNIT) 와 hp:default(2배 스케일) 두 곳을 각각 갱신한다.
        seen = {"n": 0}

        def repl(m):
            seen["n"] += 1
            factor = 1 if seen["n"] == 1 else 2
            return '<hc:intent value="%d" unit="HWPUNIT"/>' % (-indent * factor)

        new_block = re.sub(r'<hc:intent value="-?\d+" unit="HWPUNIT"/>', repl, new_block)
        if align:
            new_block = re.sub(r'<hh:align horizontal="\w+"',
                               '<hh:align horizontal="%s"' % align, new_block, count=1)
        self._new_blocks.append(new_block)
        self._blocks[new_id] = new_block
        self.cache[key] = new_id
        return new_id

    def result(self) -> str:
        if not self._new_blocks:
            return self.xml
        # 마지막 paraPr 뒤에 새 정의들을 이어 붙인다.
        idx = self.xml.rfind("</hh:paraPr>")
        if idx < 0:
            return self.xml
        idx += len("</hh:paraPr>")
        xml = self.xml[:idx] + "".join(self._new_blocks) + self.xml[idx:]
        # itemCnt 를 갱신하지 않으면 한글이 추가된 paraPr 을 무시한다.
        return re.sub(
            r'<hh:paraProperties itemCnt="\d+">',
            '<hh:paraProperties itemCnt="%d">' % self.next_id,
            xml, count=1,
        )


# ------------------------------------------------------ section0.xml 조작

def find_first(el, prefix, tag):
    want = q(prefix, tag)
    for e in el.iter():
        if e.tag == want:
            return e
    return None


def iter_tag(el, prefix, tag):
    want = q(prefix, tag)
    for e in el.iter():
        if e.tag == want:
            yield e


def content_cells(root):
    """양식 표의 내용 칸(colAddr=1)을 rowAddr 순서로 돌려준다."""
    tbl = find_first(root, "hp", "tbl")
    if tbl is None:
        raise SystemExit("템플릿에서 표를 찾지 못했습니다.")
    cells = {}
    for tc in iter_tag(tbl, "hp", "tc"):
        addr = tc.find(q("hp", "cellAddr"))
        if addr is None:
            continue
        if addr.get("colAddr") == "1":
            cells[int(addr.get("rowAddr"))] = tc
    return [cells[i] for i in sorted(cells)]


def prototype_of(tc):
    """칸의 첫 문단에서 paraPrIDRef / styleIDRef / charPrIDRef 를 뽑는다."""
    sub = tc.find(q("hp", "subList"))
    p = sub.find(q("hp", "p"))
    run = p.find(q("hp", "run"))
    return {
        "sub": sub,
        "paraPr": p.get("paraPrIDRef", "0"),
        "style": p.get("styleIDRef", "0"),
        "charPr": run.get("charPrIDRef", "0") if run is not None else "0",
    }


def make_para(para_pr, style, char_pr, text=None):
    p = ET.Element(q("hp", "p"), {
        "id": "2147483648",
        "paraPrIDRef": str(para_pr),
        "styleIDRef": str(style),
        "pageBreak": "0",
        "columnBreak": "0",
        "merged": "0",
    })
    run = ET.SubElement(p, q("hp", "run"), {"charPrIDRef": str(char_pr)})
    if text:
        t = ET.SubElement(run, q("hp", "t"))
        t.text = text
    return p, run


def em_of(header_xml: str, char_pr: str) -> int:
    m = re.search(r'<hh:charPr id="%s"[^>]*height="(\d+)"' % re.escape(str(char_pr)),
                  header_xml)
    return int(m.group(1)) if m else 1000


# ------------------------------------------------------------- 그림 삽입

MEDIA_TYPES = {".bmp": "image/bmp", ".png": "image/png", ".jpg": "image/jpeg",
               ".jpeg": "image/jpeg", ".gif": "image/gif", ".tif": "image/tiff",
               ".tiff": "image/tiff"}


def image_size_px(path):
    try:
        from PIL import Image

        with Image.open(path) as im:
            return im.size
    except Exception:
        return (1200, 640)


def make_pic(item_id, px_w, px_h, max_width):
    dim_w, dim_h = px_w * PX_TO_HWPUNIT, px_h * PX_TO_HWPUNIT
    if dim_w > max_width:
        w = max_width
        h = int(round(dim_h * max_width / float(dim_w)))
    else:
        w, h = dim_w, dim_h

    pic = ET.Element(q("hp", "pic"), {
        "id": "1", "zOrder": "0", "numberingType": "PICTURE",
        "textWrap": "TOP_AND_BOTTOM", "textFlow": "BOTH_SIDES", "lock": "0",
        "dropcapstyle": "None", "href": "", "groupLevel": "0", "instid": "1",
        "reverse": "0",
    })
    ET.SubElement(pic, q("hp", "offset"), {"x": "0", "y": "0"})
    ET.SubElement(pic, q("hp", "orgSz"), {"width": str(w), "height": str(h)})
    ET.SubElement(pic, q("hp", "curSz"), {"width": str(w), "height": str(h)})
    ET.SubElement(pic, q("hp", "flip"), {"horizontal": "0", "vertical": "0"})
    ET.SubElement(pic, q("hp", "rotationInfo"), {
        "angle": "0", "centerX": str(w // 2), "centerY": str(h // 2),
        "rotateimage": "1"})
    ri = ET.SubElement(pic, q("hp", "renderingInfo"))
    for name in ("transMatrix", "scaMatrix", "rotMatrix"):
        ET.SubElement(ri, q("hc", name), {
            "e1": "1", "e2": "0", "e3": "0", "e4": "0", "e5": "1", "e6": "0"})
    ET.SubElement(pic, q("hc", "img"), {
        "binaryItemIDRef": item_id, "bright": "0", "contrast": "0",
        "effect": "REAL_PIC", "alpha": "0"})
    rect = ET.SubElement(pic, q("hp", "imgRect"))
    for i, (x, y) in enumerate(((0, 0), (w, 0), (w, h), (0, h))):
        ET.SubElement(rect, q("hc", "pt%d" % i), {"x": str(x), "y": str(y)})
    ET.SubElement(pic, q("hp", "imgClip"), {
        "left": "0", "right": str(dim_w), "top": "0", "bottom": str(dim_h)})
    ET.SubElement(pic, q("hp", "inMargin"), {
        "left": "0", "right": "0", "top": "0", "bottom": "0"})
    ET.SubElement(pic, q("hp", "imgDim"), {
        "dimwidth": str(dim_w), "dimheight": str(dim_h)})
    ET.SubElement(pic, q("hp", "effects"))
    ET.SubElement(pic, q("hp", "sz"), {
        "width": str(w), "widthRelTo": "ABSOLUTE", "height": str(h),
        "heightRelTo": "ABSOLUTE", "protect": "0"})
    ET.SubElement(pic, q("hp", "pos"), {
        "treatAsChar": "1", "affectLSpacing": "0", "flowWithText": "1",
        "allowOverlap": "0", "holdAnchorAndSO": "0", "vertRelTo": "PARA",
        "horzRelTo": "COLUMN", "vertAlign": "TOP", "horzAlign": "LEFT",
        "vertOffset": "0", "horzOffset": "0"})
    ET.SubElement(pic, q("hp", "outMargin"), {
        "left": "0", "right": "0", "top": "0", "bottom": "0"})
    return pic


def add_manifest_item(hpf_xml: str, item_id: str, href: str, media_type: str) -> str:
    item = ('<opf:item id="%s" href="%s" media-type="%s" isEmbeded="1"/>'
            % (item_id, href, media_type))
    if item in hpf_xml:
        return hpf_xml
    return hpf_xml.replace("<opf:manifest>", "<opf:manifest>" + item, 1)


# ---------------------------------------------------------------- 렌더링

def render(spec: dict, template: str, outdir: str):
    fields = normalize_fields(spec)
    image = spec.get("image") or {}
    img_path = image.get("path")
    if img_path and not os.path.isabs(img_path):
        img_path = os.path.abspath(img_path)
    if img_path and not os.path.exists(img_path):
        print("  [경고] 그림 파일을 찾을 수 없어 건너뜁니다: %s" % img_path)
        img_path = None

    zin = zipfile.ZipFile(template)
    section = zin.read("Contents/section0.xml").decode("utf-8")
    header = zin.read("Contents/header.xml").decode("utf-8")
    hpf = zin.read("Contents/content.hpf").decode("utf-8")

    factory = ParaPrFactory(header)
    root = ET.fromstring(section)
    cells = content_cells(root)
    if len(cells) < len(ROW_LABELS):
        raise SystemExit("양식 표의 행 수(%d)가 예상(%d)과 다릅니다."
                         % (len(cells), len(ROW_LABELS)))

    counts = {}
    image_entry = None
    for idx, label in enumerate(ROW_LABELS):
        tc = cells[idx]
        proto = prototype_of(tc)
        lines = fields[label]
        counts[label] = len([l for l in lines if l.strip()])

        sub = proto["sub"]
        for p in list(sub.findall(q("hp", "p"))):
            sub.remove(p)

        em = em_of(header, proto["charPr"])
        if not lines:
            # 공란 — 빈 문단 하나만 유지한다.
            p, _ = make_para(proto["paraPr"], proto["style"], proto["charPr"])
            sub.append(p)
        else:
            for line in lines:
                indent = hanging_indent(line, em) if line.strip() else 0
                para_pr = factory.get(proto["paraPr"], indent)
                p, _ = make_para(para_pr, proto["style"], proto["charPr"],
                                 line if line.strip() else None)
                sub.append(p)

        # 「추진성과」 칸 끝에 그림 + 캡션
        if label == "추진성과" and img_path:
            cell_sz = tc.find(q("hp", "cellSz"))
            margin = tc.find(q("hp", "cellMargin"))
            width = int(cell_sz.get("width")) if cell_sz is not None else 42889
            if margin is not None:
                width -= int(margin.get("left", 0)) + int(margin.get("right", 0))
            px_w, px_h = image_size_px(img_path)
            ext = os.path.splitext(img_path)[1].lower()
            item_id = "image1"
            centered = factory.get(proto["paraPr"], 0, align="CENTER")
            p, run = make_para(centered, proto["style"], proto["charPr"])
            run.append(make_pic(item_id, px_w, px_h, int(width * 0.98)))
            sub.append(p)
            caption = (image.get("caption") or "").strip()
            if caption:
                cp, _ = make_para(centered, proto["style"], proto["charPr"], caption)
                sub.append(cp)
            hpf = add_manifest_item(hpf, item_id,
                                    "BinData/%s%s" % (item_id, ext),
                                    MEDIA_TYPES.get(ext, "image/bmp"))
            image_entry = ("BinData/%s%s" % (item_id, ext), img_path)

    section_out = XML_DECL + ET.tostring(root, encoding="unicode")
    header_out = factory.result()

    out_name = spec.get("out_name") or "정성성과.hwpx"
    if not out_name.lower().endswith(".hwpx"):
        out_name += ".hwpx"
    os.makedirs(outdir, exist_ok=True)
    out_path = os.path.join(outdir, out_name)

    replace = {
        "Contents/section0.xml": section_out.encode("utf-8"),
        "Contents/header.xml": header_out.encode("utf-8"),
        "Contents/content.hpf": hpf.encode("utf-8"),
    }
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
        # mimetype 은 첫 항목 + 무압축이어야 한다.
        try:
            zout.writestr(zipfile.ZipInfo("mimetype"), zin.read("mimetype"),
                          zipfile.ZIP_STORED)
        except KeyError:
            pass
        for item in zin.infolist():
            if item.filename == "mimetype":
                continue
            data = replace.get(item.filename, zin.read(item.filename))
            zout.writestr(item.filename, data)
        if image_entry:
            with open(image_entry[1], "rb") as fh:
                zout.writestr(image_entry[0], fh.read())
    zin.close()
    return out_path, counts, bool(image_entry)


def to_hwp(hwpx_path: str):
    """한컴오피스가 있으면 .hwp / .pdf 로도 저장한다."""
    try:
        from pyhwpx import Hwp
    except ImportError:
        print("  [건너뜀] pyhwpx 미설치 — .hwp/.pdf 변환 생략 (pip install pyhwpx)")
        return []
    made = []
    hwp = None
    try:
        hwp = Hwp(visible=False)
        hwp.open(hwpx_path)
        base = os.path.splitext(hwpx_path)[0]
        hwp.save_as(base + ".hwp", format="HWP")
        made.append(base + ".hwp")
        try:
            hwp.save_as(base + ".pdf", format="PDF")
            made.append(base + ".pdf")
        except Exception:
            pass
    except Exception as exc:
        print("  [건너뜀] 한컴오피스 변환 실패: %s" % exc)
    finally:
        if hwp is not None:
            try:
                hwp.quit()
            except Exception:
                pass
    return made


def dump_template(template: str):
    zin = zipfile.ZipFile(template)
    root = ET.fromstring(zin.read("Contents/section0.xml"))
    tbl = find_first(root, "hp", "tbl")
    print("표: %s행 × %s열" % (tbl.get("rowCnt"), tbl.get("colCnt")))
    for tc in iter_tag(tbl, "hp", "tc"):
        addr = tc.find(q("hp", "cellAddr"))
        txt = "".join(t.text or "" for t in iter_tag(tc, "hp", "t"))
        sz = tc.find(q("hp", "cellSz"))
        print("  c%s r%s  width=%s  %r" % (addr.get("colAddr"), addr.get("rowAddr"),
                                           sz.get("width") if sz is not None else "?",
                                           txt))


def main(argv=None):
    ap = argparse.ArgumentParser(description="정성성과 스펙(JSON) → 한글 문서 생성")
    ap.add_argument("--spec", help="정성성과 스펙 JSON 경로")
    ap.add_argument("--outdir", default=".", help="출력 디렉터리 (기본: 현재 폴더)")
    ap.add_argument("--template", default=None, help="정성성과 양식 .hwpx (기본: 번들 양식)")
    ap.add_argument("--to-hwp", action="store_true",
                    help="한컴오피스로 .hwp/.pdf 도 생성")
    ap.add_argument("--dump-template", action="store_true", help="양식 표 구조 출력")
    args = ap.parse_args(argv)

    template = os.path.abspath(args.template or DEFAULT_TEMPLATE)
    if not os.path.exists(template):
        raise SystemExit("양식 파일을 찾을 수 없습니다: %s" % template)

    if args.dump_template:
        dump_template(template)
        return 0

    if not args.spec:
        ap.error("--spec 또는 --dump-template 중 하나가 필요합니다.")
    with open(args.spec, encoding="utf-8") as fh:
        spec = json.load(fh)

    out_path, counts, has_image = render(spec, template, args.outdir)
    print("생성 완료: %s" % os.path.abspath(out_path))
    for label in ROW_LABELS:
        n = counts[label]
        print("  - %-14s %s" % (label, ("%d줄" % n) if n else "공란"))
    print("  - %-14s %s" % ("그림", "삽입됨" if has_image else "없음(공란)"))

    if args.to_hwp:
        for made in to_hwp(out_path):
            print("  변환: %s" % made)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
