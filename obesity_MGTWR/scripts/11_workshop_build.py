# -*- coding: utf-8 -*-
"""워크숍 발표 슬라이드 빌드: 이미 빌드된 storymap/slides.html에서 DATA 블롭을 추출해
   workshop_template.html의 /*__DATA__*/ 자리에 주입 → workshop.html
   (08_storymap_build.py처럼 원자료를 다시 읽지 않으므로 geopandas 환경 불필요)"""
import os, re

SM = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storymap")

src = open(os.path.join(SM, "slides.html"), encoding="utf-8").read()
m = re.search(r"const DATA = .*", src)  # 블롭은 한 줄(json compact)
assert m, "slides.html에서 DATA 블롭을 찾지 못함 — 08_storymap_build.py를 먼저 실행"
data_line = m.group(0)

tpl = open(os.path.join(SM, "workshop_template.html"), encoding="utf-8").read()
html = tpl.replace("/*__DATA__*/", data_line)
out = os.path.join(SM, "workshop.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print("written storymap/workshop.html:", len(html) // 1024, "KB")
