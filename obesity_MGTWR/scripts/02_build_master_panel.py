# -*- coding: utf-8 -*-
"""최종 마스터 패널 생성: 229 시군구 × 2015-2023
   DV: ob(비만율), ow(과체중이상율) — 수검수 역산 가중 집계
   IV: 주 모델 7개 + 강건성용 대안 변수 + centroid 좌표"""
import csv, os
import numpy as np

exec(open(os.path.join(os.path.dirname(__file__), "01_screen_ivs.py"),
          encoding="utf-8").read().split("# 개별 변수별 DV 상관")[0])

MAIN = ["welfare_rate", "single_hh", "divorce_rate", "log_pop_density",
        "youth_net_mig", "doctors", "apt_ratio"]
ROBUST = ["fiscal_indep", "old_housing", "youth_ratio", "elderly_ratio",
          "log_biz_density", "cultural_fac", "walk", "smoke", "drink",
          "inflow_ratio", "foreign_ratio"]

# centroid (EPSG:5179 -> km)
import geopandas as gpd
shp = gpd.read_file(os.path.join(BASE, "data", "bnd_sigungu_00_2025_2Q.shp"))
codecol = [c for c in shp.columns if "CD" in c.upper()][0]
shp["cx"] = shp.geometry.centroid.x / 1000.0
shp["cy"] = shp.geometry.centroid.y / 1000.0
cent252 = {str(r[codecol]): (r["cx"], r["cy"]) for _, r in shp.iterrows()}
# 229 기준: 통합시는 구 centroid 평균
cent = {}
for c, (x, y) in cent252.items():
    p = parent(c)
    cent.setdefault(p, []).append((x, y))
cent = {p: (float(np.mean([v[0] for v in vs])), float(np.mean([v[1] for v in vs])))
        for p, vs in cent.items()}

out = os.path.join(BASE, "output", "master_panel_2015_2023.csv")
cols = (["sgg_cd", "sgg_nm", "year", "cx_km", "cy_km", "ob", "ow"] + MAIN + ROBUST)
n_full = 0
with open(out, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(cols)
    for (sgg, y) in sorted(panel):
        row = [sgg, name229.get(sgg, ""), y,
               round(cent[sgg][0], 3) if sgg in cent else "",
               round(cent[sgg][1], 3) if sgg in cent else "",
               round(panel[(sgg, y)]["ob"], 3), round(panel[(sgg, y)]["ow"], 3)]
        vals = [X.get((sgg, y, v)) for v in MAIN + ROBUST]
        row += [("" if v is None else round(v, 4)) for v in vals]
        w.writerow(row)
        if all(X.get((sgg, y, v)) is not None for v in MAIN):
            n_full += 1
print("master panel rows:", len(panel), "| MAIN 7개 완비:", n_full,
      "| centroid 매칭:", sum(1 for s in {k[0] for k in panel} if s in cent), "/229")
