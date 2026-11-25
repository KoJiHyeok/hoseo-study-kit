#!/usr/bin/env python3
"""HWP 5.x (.hwp) -> 텍스트. 순수 표준 라이브러리만 사용 (pip 설치 불필요).

사용법: python3 tools/hwp2txt.py <파일.hwp> [...]

HWP 5.x = OLE/CFB 컨테이너. BodyText/SectionN 스트림을 (필요시 raw-deflate 해제 후)
레코드 단위로 훑어 HWPTAG_PARA_TEXT(67)의 UTF-16LE 텍스트만 뽑는다.
HWPX(zip 기반)나 구형 HWP 3.x 는 대상이 아님.
"""
import struct, sys, zlib

FREESECT, ENDOFCHAIN = 0xFFFFFFFF, 0xFFFFFFFE
# PARA_TEXT 안에서 8개 UTF-16 단위를 차지하는 확장 컨트롤 문자
EXT_CTRL = {1, 2, 3, 11, 12, 14, 15, 16, 17, 18, 21, 22, 23}
INLINE_CTRL = {4, 5, 6, 7, 8, 9, 19, 20}         # 인라인 컨트롤도 8 WCHAR (9 = 탭)


class CFB:
    """최소 기능의 Compound File Binary 리더."""

    def __init__(self, data):
        if data[:8] != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            raise ValueError("CFB 시그니처 아님 (HWP 5.x 가 아닐 수 있음)")
        self.d = data
        self.ssz = 1 << struct.unpack_from("<H", data, 0x1E)[0]
        self.mssz = 1 << struct.unpack_from("<H", data, 0x20)[0]
        n_fat, dir_start = struct.unpack_from("<I", data, 0x2C)[0], struct.unpack_from("<I", data, 0x30)[0]
        self.cutoff = struct.unpack_from("<I", data, 0x38)[0]
        mini_start, _n_mini = struct.unpack_from("<II", data, 0x3C)
        difat_start, n_difat = struct.unpack_from("<II", data, 0x44)

        difat = list(struct.unpack_from("<109I", data, 0x4C))
        sec, seen = difat_start, 0
        while sec not in (ENDOFCHAIN, FREESECT) and seen < n_difat:
            blk = self._sector(sec)
            difat += list(struct.unpack_from(f"<{self.ssz // 4 - 1}I", blk, 0))
            sec = struct.unpack_from("<I", blk, self.ssz - 4)[0]
            seen += 1

        self.fat = []
        for s in difat[:n_fat]:
            if s in (FREESECT, ENDOFCHAIN):
                continue
            self.fat += list(struct.unpack_from(f"<{self.ssz // 4}I", self._sector(s), 0))

        self.dirents = self._read_dir(dir_start)
        root = self.dirents[0]
        self.mini_fat = []
        s = mini_start
        while s not in (FREESECT, ENDOFCHAIN) and s < len(self.fat):
            self.mini_fat += list(struct.unpack_from(f"<{self.ssz // 4}I", self._sector(s), 0))
            s = self.fat[s]
        self.mini_stream = self._chain(root["start"], root["size"])

    def _sector(self, i):
        off = (i + 1) * self.ssz
        return self.d[off:off + self.ssz]

    def _chain(self, start, size):
        out, s, guard = b"", start, 0
        while s not in (FREESECT, ENDOFCHAIN) and s < len(self.fat) and guard < len(self.fat) + 8:
            out += self._sector(s)
            s = self.fat[s]
            guard += 1
        return out[:size] if size else out

    def _mini_chain(self, start, size):
        out, s, guard = b"", start, 0
        while s not in (FREESECT, ENDOFCHAIN) and s < len(self.mini_fat) and guard < len(self.mini_fat) + 8:
            out += self.mini_stream[s * self.mssz:(s + 1) * self.mssz]
            s = self.mini_fat[s]
            guard += 1
        return out[:size]

    def _read_dir(self, start):
        raw, ents = self._chain(start, 0), []
        for off in range(0, len(raw) - 127, 128):
            e = raw[off:off + 128]
            nlen = struct.unpack_from("<H", e, 0x40)[0]
            name = e[:max(nlen - 2, 0)].decode("utf-16-le", "replace")
            ents.append({
                "name": name, "type": e[0x42],
                "left": struct.unpack_from("<I", e, 0x44)[0],
                "right": struct.unpack_from("<I", e, 0x48)[0],
                "child": struct.unpack_from("<I", e, 0x4C)[0],
                "start": struct.unpack_from("<I", e, 0x74)[0],
                "size": struct.unpack_from("<Q", e, 0x78)[0],
            })
        return ents

    def paths(self):
        """{'BodyText/Section0': idx, ...} 형태로 스트림 경로를 펼친다."""
        out = {}

        def walk(i, prefix):
            if i in (FREESECT, 0xFFFFFFFF) or i >= len(self.dirents):
                return
            e = self.dirents[i]
            walk(e["left"], prefix)
            p = f"{prefix}/{e['name']}" if prefix else e["name"]
            if e["type"] == 2:
                out[p] = i
            elif e["type"] == 1:
                walk(e["child"], p)
            walk(e["right"], prefix)

        root = self.dirents[0]
        walk(root["child"], "")
        return out

    def read(self, idx):
        e = self.dirents[idx]
        return self._mini_chain(e["start"], e["size"]) if e["size"] < self.cutoff else self._chain(e["start"], e["size"])


def _para_texts(buf):
    """레코드 스트림에서 HWPTAG_PARA_TEXT(67) 문단만 뽑는다."""
    out, i, n = [], 0, len(buf)
    while i + 4 <= n:
        (hdr,) = struct.unpack_from("<I", buf, i)
        i += 4
        tag, size = hdr & 0x3FF, (hdr >> 20) & 0xFFF
        if size == 0xFFF:
            if i + 4 > n:
                break
            (size,) = struct.unpack_from("<I", buf, i)
            i += 4
        payload = buf[i:i + size]
        i += size
        if tag != 67:
            continue
        chars, j, m = [], 0, len(payload) - 1
        while j < m:
            (c,) = struct.unpack_from("<H", payload, j)
            if c in EXT_CTRL:
                j += 16                      # 확장 컨트롤 = UTF-16 8단위
            elif c in INLINE_CTRL:
                chars.append("\t" if c == 9 else " ")
                j += 16
            elif c < 32:
                chars.append("\n" if c in (10, 13) else " ")
                j += 2
            else:
                chars.append(chr(c))
                j += 2
        t = "".join(chars).strip()
        if t:
            out.append(t)
    return out


def extract(path):
    cfb = CFB(open(path, "rb").read())
    paths = cfb.paths()
    compressed = bool(struct.unpack_from("<I", cfb.read(paths["FileHeader"]), 36)[0] & 1)
    sections = sorted((p for p in paths if p.startswith("BodyText/")),
                      key=lambda p: int("".join(ch for ch in p if ch.isdigit()) or 0))
    paras = []
    for p in sections:
        buf = cfb.read(paths[p])
        if compressed:
            try:
                buf = zlib.decompress(buf, -15)
            except zlib.error:
                buf = zlib.decompressobj(-15).decompress(buf)
        paras += _para_texts(buf)
    if not paras and "PrvText" in paths:          # 폴백: 미리보기 텍스트
        paras = [cfb.read(paths["PrvText"]).decode("utf-16-le", "replace")]
    return "\n".join(paras)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for f in sys.argv[1:]:
        if len(sys.argv) > 2:
            print(f"\n===== {f} =====")
        print(extract(f))
