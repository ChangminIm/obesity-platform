# -*- coding: utf-8 -*-
"""Phase 3: MGTWR 로컬 계수 지도 (예시 스타일: RdBu_r, 0 중심, ENP 보정 t 회색 마스킹)
   + 연도별 평균 계수 추세 (IQR 밴드)
   산출: figs/coef_maps_{dv}_{year}.png (연도별 8패널), figs/coef_trends_{dv}.png,
         output/enp_critical_t_{dv}.csv"""
import os
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.spatial.distance import cdist
from scipy.stats import t as tdist

BASE = r"C:\Users\User\vibe_coding\obesity_platform\obesity_MGTWR"
OUT = os.path.join(BASE, "output")
FIG = os.path.join(BASE, "figs")
os.makedirs(FIG, exist_ok=True)

MAIN = ["welfare_rate", "single_hh", "divorce_rate", "log_pop_density",
        "youth_net_mig", "doctors", "apt_ratio"]
LABEL = {"intercept": "Intercept (geographic context)",
         "welfare_rate": "Welfare recipiency",
         "single_hh": "Single-person household",
         "divorce_rate": "Divorce rate",
         "log_pop_density": "ln population density",
         "youth_net_mig": "Youth net migration",
         "doctors": "Doctors per 1k",
         "apt_ratio": "Apartment ratio"}
DVNAME = {"ob": "infant obesity rate", "ow": "overweight+ rate"}
YEARS = list(range(2015, 2024))
GRAY = "#e8e8e8"

# ---------- 229 시군구 geometry (통합시 dissolve) ----------
shp = gpd.read_file(os.path.join(BASE, "data", "bnd_sigungu_00_2025_2Q.shp"))
codecol = [c for c in shp.columns if "CD" in c.upper()][0]
shp["sgg"] = shp[codecol].astype(str)
panel = pd.read_csv(os.path.join(OUT, "master_panel_2015_2023.csv"),
                    dtype={"sgg_cd": str})
iv_codes = set(panel.sgg_cd.unique())
shp["sgg229"] = shp["sgg"].where(shp["sgg"].isin(iv_codes), shp["sgg"].str[:4] + "0")
gdf = shp.dissolve(by="sgg229")[["geometry"]]
print("geometry:", len(gdf), "units")

# ---------- ENP_j -> 보정 임계 t ----------
def enp_j(coords, tvec, x, bw, tau):
    """univariate backfitting smoother의 hat 대각합 (adaptive bisquare)"""
    pts = np.hstack([coords, np.sqrt(tau) * tvec]) if tau > 0 else coords
    n = len(x)
    if int(bw) < 2:
        return float(n)  # bw<2: 최근접=자기자신 → 보간 수준(hat≈1), ENP≈n
    tr = 0.0
    for i in range(n):
        d = cdist([pts[i]], pts).reshape(-1)
        b = np.partition(d, int(bw) - 1)[int(bw) - 1] * 1.0000001
        w = (1 - (d / b) ** 2) ** 2
        w[d >= b] = 0
        denom = (w * x * x).sum()
        if denom > 0:
            tr += x[i] * x[i] * w[i] / denom
    return tr

panel = panel.sort_values(["sgg_cd", "year"]).reset_index(drop=True)
coords = panel[["cx_km", "cy_km"]].to_numpy(float)
tvec = panel[["year"]].to_numpy(float)
Xz = (panel[MAIN] - panel[MAIN].mean()) / panel[MAIN].std()
comp = pd.read_csv(os.path.join(OUT, "model_comparison.csv"))

DVS = tuple(os.environ.get("DVS", "ob,ow").split(","))
for dv in DVS:
    bwt = pd.read_csv(os.path.join(OUT, f"bandwidths_{dv}_mgtwr.csv"))
    enp_total = float(comp[(comp.dv == dv) & (comp.model == "MGTWR")].enp.iloc[0])
    dof = len(panel) - enp_total
    rows = []
    for _, r in bwt.iterrows():
        v = r["variable"]
        x = np.ones(len(panel)) if v == "intercept" else Xz[v].to_numpy(float)
        e = enp_j(coords, tvec, x, r["bw_spatial"], r["tau_temporal"])
        alpha = 0.05 / max(e, 1.0)          # da Silva & Fotheringham 보정
        tcrit = tdist.ppf(1 - alpha / 2, dof)
        rows.append(dict(variable=v, ENP_j=e, alpha_adj=alpha, t_crit=tcrit))
        print(f"{dv} {v:<16} ENP_j={e:8.1f} t_crit={tcrit:.2f}", flush=True)
    enp_df = pd.DataFrame(rows).set_index("variable")
    enp_df.to_csv(os.path.join(OUT, f"enp_critical_t_{dv}.csv"))

    co = pd.read_csv(os.path.join(OUT, f"local_coefs_{dv}_MGTWR.csv"),
                     dtype={"sgg_cd": str})
    allv = ["intercept"] + MAIN
    # 변수별 색 범위(전 연도 공통, 대칭) — 연도 간 비교 가능
    vmax = {v: max(abs(np.percentile(co["b_" + v], 2)),
                   abs(np.percentile(co["b_" + v], 98))) for v in allv}

    # ---------- 연도별 8패널 지도 ----------
    for yr in YEARS:
        sub = co[co.year == yr].set_index("sgg_cd")
        fig, axes = plt.subplots(2, 4, figsize=(26, 15))
        for ax, v in zip(axes.flat, allv):
            g = gdf.join(sub[["b_" + v, "t_" + v]])
            sig = g["t_" + v].abs() >= enp_df.loc[v, "t_crit"]
            g.plot(ax=ax, color=GRAY, edgecolor="white", linewidth=0.2)
            if sig.any():
                g[sig].plot(ax=ax, column="b_" + v, cmap="RdBu_r",
                            vmin=-vmax[v], vmax=vmax[v],
                            edgecolor="white", linewidth=0.2, legend=True,
                            legend_kwds={"shrink": 0.75})
            ax.set_title(f"{LABEL[v]}\n{yr}, gray = n.s. (ENP-adjusted t)",
                         fontsize=13)
            ax.set_axis_off()
        fig.suptitle(f"MGTWR local coefficients, {DVNAME[dv]} "
                     f"(adjusted-t masked) — {yr}", fontsize=18, y=0.99)
        fig.tight_layout()
        fig.savefig(os.path.join(FIG, f"coef_maps_{dv}_{yr}.png"),
                    dpi=130, bbox_inches="tight")
        plt.close(fig)
        print(f"saved coef_maps_{dv}_{yr}.png", flush=True)

    # ---------- 연도별 평균 계수 추세 (IQR 밴드) ----------
    fig, axes = plt.subplots(2, 4, figsize=(24, 9))
    for ax, v in zip(axes.flat, allv):
        gby = co.groupby("year")["b_" + v]
        m, q1, q3 = gby.mean(), gby.quantile(.25), gby.quantile(.75)
        ax.fill_between(m.index, q1, q3, color="#aecde8", alpha=0.6)
        ax.plot(m.index, m.values, "-o", color="#2470a8", ms=4)
        ax.axhline(0, color="gray", lw=0.8)
        ax.set_title(LABEL[v], fontsize=12)
        ax.set_xticks(YEARS)
        ax.tick_params(labelsize=9)
    fig.suptitle(f"MGTWR mean local coefficient by year, {DVNAME[dv]} "
                 f"(band = IQR across sigungu)", fontsize=16)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, f"coef_trends_{dv}.png"),
                dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"saved coef_trends_{dv}.png", flush=True)

print("ALL MAPS DONE")
