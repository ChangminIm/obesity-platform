# -*- coding: utf-8 -*-
"""퀸 인접 + 도서 최근접 연결(행표준화) 가중행렬로 모든 Moran's I 재계산
   (EHSA 플랫폼의 '섬연결 가중'과 동일 사상)
   - DV 자체(연도별) + 5개 모형 잔차(연도별 평균) × 2 DV
   - OLS/GWR/GTWR: 저장된 bandwidth로 재적합, MGWR/MGTWR: 저장 계수로 잔차 복원
   산출: output/moran_queen_dv.csv, output/moran_queen_resid.csv"""
import os
import numpy as np
import pandas as pd
import geopandas as gpd
import libpysal
from libpysal.weights import Queen, KNN
from libpysal.weights.util import attach_islands
from esda.moran import Moran

BASE = r"C:\Users\User\vibe_coding\obesity_platform\obesity_MGTWR"
OUT = os.path.join(BASE, "output")
MAIN = ["welfare_rate", "single_hh", "divorce_rate", "log_pop_density",
        "youth_net_mig", "doctors", "apt_ratio"]
YEARS = list(range(2015, 2024))

# ---- W: Queen + 도서 연결 (원본 dissolve 지오메트리 기준) ----
gdf = gpd.read_file(os.path.join(BASE, "data", "sgg229_dissolved.gpkg"))
gdf = gdf.sort_values("sgg229").reset_index(drop=True)
wq = Queen.from_dataframe(gdf, use_index=False)
print("queen islands:", [gdf.sgg229[i] for i in wq.islands], flush=True)
cent = np.column_stack([gdf.geometry.centroid.x, gdf.geometry.centroid.y])
if wq.islands:
    w1 = KNN.from_array(cent, k=1)
    wq = attach_islands(wq, w1)
    print("after attach: islands =", wq.islands, flush=True)

# 다중 구성 컴포넌트(예: 제주시-서귀포시)도 본토 최근접 쌍으로 연결
from scipy.spatial.distance import cdist
lab = np.asarray(wq.component_labels)
if len(set(lab)) > 1:
    main = np.bincount(lab).argmax()
    nb = {k: list(v) for k, v in wq.neighbors.items()}
    ids = np.asarray(wq.id_order)
    for comp in sorted(set(lab) - {main}):
        ci = np.where(lab == comp)[0]
        mi = np.where(lab == main)[0]
        d = cdist(cent[ci], cent[mi])
        i, j = np.unravel_index(d.argmin(), d.shape)
        a, b = ids[ci[i]], ids[mi[j]]
        nb[a].append(b)
        nb[b].append(a)
        print(f"bridge: {a} <-> {b}", flush=True)
    wq = libpysal.weights.W(nb, id_order=list(ids))
print("final components:", len(set(np.asarray(wq.component_labels))), flush=True)
wq.transform = "r"
order = list(gdf.sgg229)  # W의 행 순서 = sgg 코드 정렬

panel = pd.read_csv(os.path.join(OUT, "master_panel_2015_2023.csv"), dtype={"sgg_cd": str})
panel = panel.sort_values(["sgg_cd", "year"]).reset_index(drop=True)
assert list(panel[panel.year == 2015].sgg_cd) == order

def z(a):
    a = np.asarray(a, float)
    return (a - a.mean(0)) / a.std(0)

Xz = z(panel[MAIN].to_numpy(float))
coords = panel[["cx_km", "cy_km"]].to_numpy(float)
tarr = panel[["year"]].to_numpy(float)
yearv = panel.year.to_numpy()

def yearly_moran(vec):
    return [float(Moran(vec[yearv == y], wq, permutations=0).I) for y in YEARS]

# ---- DV 자체 (999 순열 p 포함) ----
rows = []
for dv in ("ob", "ow"):
    for y in YEARS:
        m = Moran(panel.loc[panel.year == y, dv].to_numpy(float), wq, permutations=999)
        rows.append(dict(dv=dv, year=y, I=round(m.I, 3), p=round(m.p_sim, 3)))
pd.DataFrame(rows).to_csv(os.path.join(OUT, "moran_queen_dv.csv"), index=False)
print("dv moran(queen) saved", flush=True)

# ---- 모형 잔차 ----
from mgtwr.model import GWR, GTWR
mc = pd.read_csv(os.path.join(OUT, "model_comparison.csv"))
res_rows = []
for dv in ("ob", "ow"):
    yz = z(panel[[dv]].to_numpy(float))
    resids = {}
    # OLS
    Xo = np.column_stack([np.ones(len(yz)), Xz])
    b, *_ = np.linalg.lstsq(Xo, yz[:, 0], rcond=None)
    resids["OLS"] = yz[:, 0] - Xo @ b
    # GWR / GTWR 재적합 (저장 bandwidth)
    bw_g = float(mc[(mc.dv == dv) & (mc.model == "GWR")].bw.iloc[0])
    r = GWR(coords, Xz, yz, bw_g, kernel="bisquare", fixed=False, thread=10).fit()
    resids["GWR"] = r.reside.flatten()
    row = mc[(mc.dv == dv) & (mc.model == "GTWR")].iloc[0]
    r = GTWR(coords, tarr, Xz, yz, float(row.bw), float(row.tau),
             kernel="bisquare", fixed=False, thread=10).fit()
    resids["GTWR"] = r.reside.flatten()
    # MGWR / MGTWR: 저장 계수로 잔차 복원
    for tag in ("MGWR", "MGTWR"):
        co = pd.read_csv(os.path.join(OUT, f"local_coefs_{dv}_{tag}.csv"),
                         dtype={"sgg_cd": str}).sort_values(["sgg_cd", "year"]).reset_index(drop=True)
        pred = co["b_intercept"].to_numpy()
        for j, v in enumerate(MAIN):
            pred = pred + co["b_" + v].to_numpy() * Xz[:, j]
        resids[tag] = yz[:, 0] - pred
    for mname, rv in resids.items():
        vals = yearly_moran(rv)
        res_rows.append(dict(dv=dv, model=mname,
                             moran_queen=round(float(np.mean(vals)), 3)))
        print(dv, mname, "moran_queen =", round(float(np.mean(vals)), 3), flush=True)

pd.DataFrame(res_rows).to_csv(os.path.join(OUT, "moran_queen_resid.csv"), index=False)
print("DONE")
