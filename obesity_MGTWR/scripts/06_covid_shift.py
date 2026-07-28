# -*- coding: utf-8 -*-
"""Phase 4-1: 코로나 전후 로컬 계수 변화
   (a) 2019 vs 2020 단순 비교  (b) 이전(2015-2019 평균) vs 이후(2020-2023 평균)
   산출: output/covid_shift_{dv}.csv, figs/covid_diff_maps_{dv}.png,
         figs/covid_diff_maps_1920_{dv}.png"""
import os
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import ttest_rel

BASE = r"C:\Users\User\vibe_coding\obesity_platform\obesity_MGTWR"
OUT = os.path.join(BASE, "output")
FIG = os.path.join(BASE, "figs")
GPKG = os.path.join(BASE, "data", "sgg229_dissolved.gpkg")

MAIN = ["welfare_rate", "single_hh", "divorce_rate", "log_pop_density",
        "youth_net_mig", "doctors", "apt_ratio"]
LABEL = {"intercept": "Intercept", "welfare_rate": "Welfare recipiency",
         "single_hh": "Single-person hh", "divorce_rate": "Divorce rate",
         "log_pop_density": "ln pop density", "youth_net_mig": "Youth net mig.",
         "doctors": "Doctors per 1k", "apt_ratio": "Apartment ratio"}
DVNAME = {"ob": "infant obesity rate", "ow": "overweight+ rate"}
ALLV = ["intercept"] + MAIN
PRE = list(range(2015, 2020))
POST = list(range(2020, 2024))

# ---------- geometry (dissolve 1회 후 캐시) ----------
if os.path.exists(GPKG):
    gdf = gpd.read_file(GPKG).set_index("sgg229")
else:
    shp = gpd.read_file(os.path.join(BASE, "data", "bnd_sigungu_00_2025_2Q.shp"))
    codecol = [c for c in shp.columns if "CD" in c.upper()][0]
    shp["sgg"] = shp[codecol].astype(str)
    panel = pd.read_csv(os.path.join(OUT, "master_panel_2015_2023.csv"),
                        dtype={"sgg_cd": str})
    iv = set(panel.sgg_cd.unique())
    shp["sgg229"] = shp["sgg"].where(shp["sgg"].isin(iv), shp["sgg"].str[:4] + "0")
    gdf = shp.dissolve(by="sgg229")[["geometry"]]
    gdf.reset_index().to_file(GPKG, driver="GPKG")
print("geometry ready:", len(gdf), flush=True)

def diff_fig(gdf_joined, diffs, title, path):
    fig, axes = plt.subplots(2, 4, figsize=(26, 15))
    for ax, v in zip(axes.flat, ALLV):
        col = "d_" + v
        vmax = max(abs(np.percentile(diffs[col], 2)),
                   abs(np.percentile(diffs[col], 98)), 1e-9)
        g = gdf_joined.join(diffs[[col]])
        g.plot(ax=ax, column=col, cmap="RdBu_r", vmin=-vmax, vmax=vmax,
               edgecolor="white", linewidth=0.2, legend=True,
               legend_kwds={"shrink": 0.75})
        ax.set_title(LABEL[v], fontsize=13)
        ax.set_axis_off()
    fig.suptitle(title, fontsize=18, y=0.99)
    fig.tight_layout()
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print("saved", os.path.basename(path), flush=True)

for dv in ("ob", "ow"):
    co = pd.read_csv(os.path.join(OUT, f"local_coefs_{dv}_MGTWR.csv"),
                     dtype={"sgg_cd": str})
    rows = []
    d1920 = pd.DataFrame(index=sorted(co.sgg_cd.unique()))
    dprepost = pd.DataFrame(index=sorted(co.sgg_cd.unique()))
    for v in ALLV:
        piv = co.pivot_table(index="sgg_cd", columns="year", values="b_" + v)
        b19, b20 = piv[2019], piv[2020]
        pre, post = piv[PRE].mean(axis=1), piv[POST].mean(axis=1)
        t1, p1 = ttest_rel(b20, b19)
        t2, p2 = ttest_rel(post, pre)
        rows.append(dict(
            variable=v,
            mean_2019=b19.mean(), mean_2020=b20.mean(),
            diff_1920=(b20 - b19).mean(), pct_up_1920=100 * ((b20 - b19) > 0).mean(),
            paired_t_1920=t1, p_1920=p1,
            mean_pre=pre.mean(), mean_post=post.mean(),
            diff_prepost=(post - pre).mean(),
            pct_up_prepost=100 * ((post - pre) > 0).mean(),
            paired_t_prepost=t2, p_prepost=p2))
        d1920["d_" + v] = b20 - b19
        dprepost["d_" + v] = post - pre
    res = pd.DataFrame(rows)
    res.to_csv(os.path.join(OUT, f"covid_shift_{dv}.csv"), index=False)
    print(res.round(3).to_string(index=False), flush=True)

    diff_fig(gdf, dprepost,
             f"Change in MGTWR local coefficients, {DVNAME[dv]}: "
             f"post (2020-23 mean) minus pre (2015-19 mean)",
             os.path.join(FIG, f"covid_diff_maps_{dv}.png"))
    diff_fig(gdf, d1920,
             f"Change in MGTWR local coefficients, {DVNAME[dv]}: 2020 minus 2019",
             os.path.join(FIG, f"covid_diff_maps_1920_{dv}.png"))

print("COVID SHIFT DONE")
