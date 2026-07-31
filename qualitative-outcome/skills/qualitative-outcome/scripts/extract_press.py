#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""보도자료(.hwp / .hwpx / .txt / .md) 에서 본문 텍스트·삽입 이미지·URL 을 추출한다.

사용법
------
  python extract_press.py "보도자료.hwp"
  python extract_press.py "보도자료.hwp" --images-dir ./_press_images
  python extract_press.py "보도자료.hwp" --json out.json

출력(JSON)
----------
  {
    "source": "...",
    "text": "보도자료 전문",
    "images": [{"index":1,"name":"BIN0001.bmp","path":"...","width":1229,"height":653}],
    "links": ["https://..."]
  }
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import struct
import sys
import zipfile

# stdout 인코딩 고정(윈도우 cp949 회피)
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass


# ---------------------------------------------------------------- HWP(바이너리)

# 8바이트가 아니라 '확장 제어문자'(inline/extended)는 16바이트를 차지한다.
_HWP_EXTENDED_CTRL = {1, 2, 3, 11, 12, 14, 15, 16, 17, 18, 21, 22, 23}
_HWPTAG_PARA_TEXT = 67


def _hwp_parse_section(data: bytes) -> str:
    """BodyText 스트림(비압축 상태)에서 문단 텍스트만 뽑는다."""
    out, i, n = [], 0, len(data)
    while i + 4 <= n:
        header = struct.unpack_from("<I", data, i)[0]
        tag = header & 0x3FF
        size = (header >> 20) & 0xFFF
        i += 4
        if size == 0xFFF:
            if i + 4 > n:
                break
            size = struct.unpack_from("<I", data, i)[0]
            i += 4
        payload = data[i:i + size]
        i += size
        if tag != _HWPTAG_PARA_TEXT:
            continue
        buf, j = [], 0
        while j + 1 < len(payload):
            ch = struct.unpack_from("<H", payload, j)[0]
            if ch in (10, 13):
                buf.append("\n")
                j += 2
            elif ch == 0:
                j += 2
            elif ch < 32:
                j += 16 if ch in _HWP_EXTENDED_CTRL else 2
            else:
                buf.append(chr(ch))
                j += 2
        out.append("".join(buf))
    return "\n".join(out)


def _sniff_image_ext(blob: bytes, fallback: str) -> str:
    sigs = [
        (b"\x89PNG\r\n\x1a\n", ".png"),
        (b"\xff\xd8\xff", ".jpg"),
        (b"GIF8", ".gif"),
        (b"BM", ".bmp"),
        (b"II*\x00", ".tif"),
        (b"MM\x00*", ".tif"),
    ]
    for sig, ext in sigs:
        if blob.startswith(sig):
            return ext
    return fallback or ".bin"


def extract_hwp(path: str, images_dir: str | None):
    try:
        import olefile
    except ImportError:
        raise SystemExit(
            "바이너리 .hwp 를 읽으려면 olefile 이 필요합니다:  pip install olefile"
        )
    import zlib

    ole = olefile.OleFileIO(path)
    try:
        header = ole.openstream("FileHeader").read()
        compressed = bool(header[36] & 0x01)

        entries = ole.listdir()
        sections = sorted(
            [e for e in entries if e and e[0] == "BodyText"],
            key=lambda e: int(re.sub(r"\D", "", e[-1]) or 0),
        )
        chunks = []
        for entry in sections:
            raw = ole.openstream(entry).read()
            if compressed:
                try:
                    raw = zlib.decompress(raw, -15)
                except zlib.error:
                    continue
            chunks.append(_hwp_parse_section(raw))
        text = "\n".join(chunks)

        images = []
        bins = sorted(
            [e for e in entries if e and e[0] == "BinData"],
            key=lambda e: e[-1],
        )
        for idx, entry in enumerate(bins, 1):
            blob = ole.openstream(entry).read()
            if compressed:
                try:
                    blob = zlib.decompress(blob, -15)
                except zlib.error:
                    pass  # BinData 는 개별적으로 비압축일 수 있다
            name = entry[-1]
            images.append(_save_image(blob, name, idx, images_dir))
    finally:
        ole.close()
    return text, images


# ------------------------------------------------------------------- HWPX

def _strip_ns(tag: str) -> str:
    return tag.split("}")[-1]


def extract_hwpx(path: str, images_dir: str | None):
    import xml.etree.ElementTree as ET

    zf = zipfile.ZipFile(path)
    names = zf.namelist()

    lines = []
    sections = sorted(n for n in names if re.match(r"Contents/section\d+\.xml$", n))
    for sec in sections:
        root = ET.fromstring(zf.read(sec))
        for el in root.iter():
            if _strip_ns(el.tag) != "p":
                continue
            txt = "".join(
                t.text or "" for t in el.iter() if _strip_ns(t.tag) == "t"
            )
            lines.append(txt)
    text = "\n".join(lines)

    images = []
    for idx, n in enumerate(sorted(x for x in names if x.startswith("BinData/")), 1):
        images.append(_save_image(zf.read(n), os.path.basename(n), idx, images_dir))
    return text, images


# ------------------------------------------------------------------ 공통

def _save_image(blob: bytes, name: str, idx: int, images_dir: str | None):
    ext = _sniff_image_ext(blob, os.path.splitext(name)[1].lower())
    info = {"index": idx, "name": name, "path": None, "width": None, "height": None,
            "bytes": len(blob)}
    if images_dir:
        os.makedirs(images_dir, exist_ok=True)
        out = os.path.join(images_dir, "press_image%d%s" % (idx, ext))
        with open(out, "wb") as fh:
            fh.write(blob)
        info["path"] = os.path.abspath(out)
    try:
        from PIL import Image

        with Image.open(io.BytesIO(blob)) as im:
            info["width"], info["height"] = im.size
    except Exception:
        pass
    return info


def extract_plain(path: str):
    for enc in ("utf-8", "cp949", "utf-16"):
        try:
            with open(path, encoding=enc) as fh:
                return fh.read(), []
        except (UnicodeDecodeError, UnicodeError):
            continue
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read(), []


_URL_RE = re.compile(r"https?://[^\s\"'<>()ㄱ-힝]+")


def find_links(text: str):
    seen, out = set(), []
    for m in _URL_RE.finditer(text):
        url = m.group(0).rstrip(".,;)]」』")
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out


def normalize(text: str) -> str:
    text = text.replace("\xa0", " ").replace("　", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract(path: str, images_dir: str | None):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".hwp":
        text, images = extract_hwp(path, images_dir)
    elif ext in (".hwpx", ".hwt"):
        text, images = extract_hwpx(path, images_dir)
    elif ext in (".txt", ".md", ".text"):
        text, images = extract_plain(path)
    else:
        raise SystemExit(
            "지원하지 않는 형식입니다: %s (지원: .hwp, .hwpx, .txt, .md)" % ext
        )
    text = normalize(text)
    return {
        "source": os.path.abspath(path),
        "text": text,
        "images": images,
        "links": find_links(text),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="보도자료에서 본문·이미지·링크를 추출")
    ap.add_argument("press", help="보도자료 파일 (.hwp/.hwpx/.txt/.md)")
    ap.add_argument("--images-dir", default=None,
                    help="삽입 이미지를 저장할 디렉터리 (지정 시에만 저장)")
    ap.add_argument("--json", default=None, help="결과 JSON 저장 경로")
    ap.add_argument("--text-only", action="store_true", help="본문 텍스트만 출력")
    args = ap.parse_args(argv)

    if not os.path.exists(args.press):
        raise SystemExit("파일을 찾을 수 없습니다: %s" % args.press)

    result = extract(args.press, args.images_dir)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
        print("추출 결과 저장: %s" % os.path.abspath(args.json))

    if args.text_only:
        print(result["text"])
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
