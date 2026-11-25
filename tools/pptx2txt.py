#!/usr/bin/env python3
"""PPTX -> 슬라이드별 텍스트. 표준 라이브러리만 사용 (pptx 패키지 불필요).

사용법: python3 tools/pptx2txt.py <파일.pptx> [...]
슬라이드 노트(notesSlide)도 있으면 함께 뽑는다.
"""
import re, sys, zipfile
import xml.etree.ElementTree as ET

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}t"


def _texts(z, name):
    return [e.text for e in ET.fromstring(z.read(name)).iter(A) if e.text and e.text.strip()]


def extract(path):
    z = zipfile.ZipFile(path)
    slides = sorted((n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                    key=lambda s: int(re.findall(r"\d+", s)[0]))
    notes = {int(re.findall(r"\d+", n)[0]): n
             for n in z.namelist() if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", n)}
    out = [f"# {path}  (슬라이드 {len(slides)}장, 미디어 "
           f"{len([n for n in z.namelist() if n.startswith('ppt/media/')])}개)"]
    for n in slides:
        i = int(re.findall(r"\d+", n)[0])
        out.append(f"\n--- slide {i} ---\n" + " ".join(_texts(z, n)))
        if i in notes:
            t = " ".join(_texts(z, notes[i])).strip()
            if t:
                out.append(f"[노트] {t}")
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for f in sys.argv[1:]:
        print(extract(f))
