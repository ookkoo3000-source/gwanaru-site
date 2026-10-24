# -*- coding: utf-8 -*-
"""img/*.jpg → 같은 이름의 .webp 생성(없거나 원본이 더 새로울 때만). 긴 변 1600px 초과면 줄임. 원본 jpg는 그대로 둠(fallback).
    python -I tools_images.py"""
import pathlib, sys
from PIL import Image
sys.stdout.reconfigure(encoding="utf-8")
root = pathlib.Path(__file__).parent / "img"
for jpg in sorted(root.glob("*.jpg")):
    webp = jpg.with_suffix(".webp")
    if webp.exists() and webp.stat().st_mtime >= jpg.stat().st_mtime: continue
    im = Image.open(jpg).convert("RGB")
    w, h = im.size
    if max(w, h) > 1600:
        s = 1600 / max(w, h); im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
    im.save(webp, "WEBP", quality=78, method=6)
    print(f"{jpg.name} {jpg.stat().st_size//1024}KB → {webp.name} {webp.stat().st_size//1024}KB ({im.size[0]}x{im.size[1]})")
