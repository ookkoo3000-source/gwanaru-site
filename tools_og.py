# -*- coding: utf-8 -*-
"""img/og.png 생성(1200x630). 사이트 이름·문구·전화만. 실행: python -I tools_og.py"""
import pathlib, sys
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(pathlib.Path(__file__).parent / "data")); import content as D  # noqa
sys.stdout.reconfigure(encoding="utf-8")
W, H = 1200, 630
im = Image.new("RGB", (W, H), "#10243a"); d = ImageDraw.Draw(im)
def font(size, bold=True):
    for p in (["C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf"] if bold else ["C:/Windows/Fonts/malgun.ttf"]):
        if pathlib.Path(p).exists(): return ImageFont.truetype(p, size)
    return ImageFont.load_default()
# 마크
d.rounded_rectangle((80, 80, 150, 150), 16, fill="#1b3550")
d.line([(95, 125), (112, 112), (130, 125), (138, 118)], fill="#45c2b6", width=6, joint="curve")
d.line([(95, 108), (112, 95), (130, 108), (138, 101)], fill="#ffffff", width=6, joint="curve")
d.text((170, 92), D.SITE_NAME, font=font(44), fill="#ffffff")
lines = D.TAGLINE.split("\n")
y = 230
for ln in lines:
    d.text((80, y), ln, font=font(62), fill="#ffffff"); y += 84
d.text((80, y + 24), "초·중·고 1:1 방문·화상 과외 상담 · " + D.TRIAL, font=font(30, False), fill="#b4c2cf")
d.rounded_rectangle((80, 500, 80 + 340, 560), 10, fill="#0f7c74")
d.text((104, 511), "전화 " + D.PHONE, font=font(30), fill="#ffffff")
out = pathlib.Path(__file__).parent / "img" / "og.png"; im.save(out, optimize=True)
print(out, out.stat().st_size // 1024, "KB")
