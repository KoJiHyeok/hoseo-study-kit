"""할일.app 아이콘 — 종이색 바탕 + 'LMS' 글자 + 형광펜 밑줄. 실행: ~/.venvs/stt/bin/python make_icon.py <out.png>"""
import sys
from PIL import Image, ImageDraw, ImageFont

S = 1024
im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
d.rounded_rectangle((100, 100, 924, 924), radius=190, fill=(253, 251, 243), outline=(226, 222, 208), width=6)
for y in range(260, 900, 96):                                   # 노트 줄
    d.line((150, y, 874, y), fill=(223, 231, 241), width=6)
d.line((210, 120, 210, 904), fill=(242, 167, 167), width=8)     # 빨간 여백선

font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Black.ttf", 270)
text = "LMS"
l, t, r, b = d.textbbox((0, 0), text, font=font)
x, y = (S - (r - l)) / 2 - l + 20, (S - (b - t)) / 2 - t - 10

hl = Image.new("RGBA", (S, S), (0, 0, 0, 0))                    # 살짝 기운 형광펜
ImageDraw.Draw(hl).rounded_rectangle((x - 30, y + (b - t) * 0.55, x + (r - l) + 30, y + (b - t) + 40),
                                     radius=18, fill=(255, 242, 122))
im.alpha_composite(hl.rotate(2.5, center=(S / 2, S / 2)))
d = ImageDraw.Draw(im)
d.text((x, y), text, font=font, fill=(29, 29, 31))
im.save(sys.argv[1])
