# -*- coding: utf-8 -*-
"""Phase 2: OLS -> GWR -> MGWR -> GTWR -> MGTWR 비교 (DV: ob, ow)
   입력: output/master_panel_2015_2023.csv
   출력: output/model_comparison.csv, output/bandwidths_<dv>.csv,
         output/local_coefs_<dv>_<model>.csv, output/models_log.txt"""
import os, time
import numpy as np
import pandas as pd

BASE = r"C:\Users\User\vibe_coding\obesity_platform\obesity_MGTWR"
OUT = os.path.join(BASE, "output")
LOG = os.path.join(OUT, "models_log.txt")
MAIN = ["welfare_rate", "single_hh", "divorce_rate", "log_pop_density",
        "youth_net_mig", "doctors", "apt_ratio"]
THREAD = 10

def log(msg):
    line = time.strftime("[%H:%M:%S] ") + msg
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

df = pd.read_csv(os.path.join(OUT, "master_panel_2015_2023.csv"))
df = df.sort_values(["sgg_cd", "year"]).reset_index(drop=True)
coords = df[["cx_km", "cy_km"]].to_numpy(float)
tarr = df[["year"]].to_numpy(float)

def z(a):
    a = np.asarray(a, float)
    return (a - a.mean(0)) / a.std(0)

Xz = z(df[MAIN].to_numpy(float))

# Moran's I (연도별 KNN8, 잔차)
from libpysal.weights import KNN
from esda.moran import Moran
sgg_coord = df[df.year == 2015][["cx_km", "cy_km"]].to_numpy(float)
W = KNN.from_array(sgg_coord, k=8)
W.transform = "r"

def resid_moran(res_vec):
    vals = []
    for y in sorted(df.year.unique()):
        m = Moran(res_vec[df.year.values == y], W, permutations=0)
        vals.append(m.I)
    return float(np.mean(vals))

def aicc_ols(rss, n, k):
    llf = -n / 2 * (np.log(2 * np.pi * rss / n) + 1)
    p = k + 1
    return -2 * llf + 2 * p + 2 * p * (p + 1) / (n - p - 1)

rows = []
for dv in ("ob", "ow"):
    yz = z(df[[dv]].to_numpy(float))
    n = len(yz)

    # ---- OLS ----
    Xo = np.column_stack([np.ones(n), Xz])
    b, *_ = np.linalg.lstsq(Xo, yz[:, 0], rcond=None)
    res = yz[:, 0] - Xo @ b
    rss = float((res ** 2).sum())
    r2 = 1 - rss / n
    k = Xz.shape[1]
    rows.append(dict(dv=dv, model="OLS", aicc=aicc_ols(rss, n, k), R2=r2,
                     adj_R2=1 - (1 - r2) * (n - 1) / (n - k - 1),
                     rmse=np.sqrt(rss / n), enp=k + 1, bw="", tau="",
                     moran=resid_moran(res)))
    log(f"{dv} OLS done aicc={rows[-1]['aicc']:.1f} moran={rows[-1]['moran']:.3f}")

    from mgtwr.sel import (SearchGWRParameter, SearchMGWRParameter,
                           SearchGTWRParameter, SearchMGTWRParameter)
    from mgtwr.model import GWR, MGWR, GTWR, MGTWR

    # ---- GWR ----
    t0 = time.time()
    sel_g = SearchGWRParameter(coords, Xz, yz, kernel="bisquare", fixed=False, thread=THREAD)
    bw = sel_g.search(bw_max=1000, verbose=False)
    gwr = GWR(coords, Xz, yz, bw, kernel="bisquare", fixed=False, thread=THREAD).fit()
    rows.append(dict(dv=dv, model="GWR", aicc=gwr.aicc, R2=gwr.R2, adj_R2=gwr.adj_R2,
                     rmse=float(np.sqrt((gwr.reside ** 2).mean())), enp=float(gwr.ENP),
                     bw=bw, tau="", moran=resid_moran(gwr.reside.flatten())))
    log(f"{dv} GWR done bw={bw} aicc={gwr.aicc:.1f} ({time.time()-t0:.0f}s)")

    # ---- MGWR ----
    t0 = time.time()
    sel_mg = SearchMGWRParameter(coords, Xz, yz, kernel="bisquare", fixed=False, thread=THREAD)
    sel_mg.search(bw_max=1000, tol_multi=1.0e-4, bws_same_times=3, verbose=False)
    mgwr = MGWR(coords, Xz, yz, sel_mg, kernel="bisquare", fixed=False, thread=THREAD).fit()
    bws = list(np.ravel(mgwr.bws))
    rows.append(dict(dv=dv, model="MGWR", aicc=mgwr.aic_c, R2=mgwr.R2, adj_R2=mgwr.adj_R2,
                     rmse=float(np.sqrt((mgwr.reside ** 2).mean())), enp=float(mgwr.ENP),
                     bw=";".join(str(x) for x in bws), tau="",
                     moran=resid_moran(mgwr.reside.flatten())))
    log(f"{dv} MGWR done bws={bws} aicc={mgwr.aic_c:.1f} ({time.time()-t0:.0f}s)")
    pd.DataFrame({"variable": ["intercept"] + MAIN, "bw_mgwr": bws}
                 ).to_csv(os.path.join(OUT, f"bandwidths_{dv}_mgwr.csv"), index=False)

    # ---- GTWR ----
    t0 = time.time()
    sel_gt = SearchGTWRParameter(coords, tarr, Xz, yz, kernel="bisquare", fixed=False, thread=THREAD)
    bw_g, tau_g = sel_gt.search(tau_max=300, verbose=False)
    gtwr = GTWR(coords, tarr, Xz, yz, bw_g, tau_g, kernel="bisquare", fixed=False, thread=THREAD).fit()
    rows.append(dict(dv=dv, model="GTWR", aicc=gtwr.aicc, R2=gtwr.R2, adj_R2=gtwr.adj_R2,
                     rmse=float(np.sqrt((gtwr.reside ** 2).mean())), enp=float(gtwr.ENP),
                     bw=bw_g, tau=tau_g, moran=resid_moran(gtwr.reside.flatten())))
    log(f"{dv} GTWR done bw={bw_g} tau={tau_g} aicc={gtwr.aicc:.1f} ({time.time()-t0:.0f}s)")

    # ---- MGTWR ----
    t0 = time.time()
    sel_mgt = SearchMGTWRParameter(coords, tarr, Xz, yz, kernel="bisquare", fixed=False, thread=THREAD)
    sel_mgt.search(tau_max=300, tol_multi=1.0e-4, verbose=False)
    mgt = MGTWR(coords, tarr, Xz, yz, sel_mgt, kernel="bisquare", fixed=False, thread=THREAD).fit()
    rows.append(dict(dv=dv, model="MGTWR", aicc=mgt.aic_c, R2=mgt.R2, adj_R2=mgt.adj_R2,
                     rmse=float(np.sqrt((mgt.reside ** 2).mean())), enp=float(mgt.ENP),
                     bw=";".join(str(x) for x in np.ravel(mgt.bw_ts)),
                     tau=";".join(str(x) for x in np.ravel(mgt.taus)),
                     moran=resid_moran(mgt.reside.flatten())))
    log(f"{dv} MGTWR done aicc={mgt.aic_c:.1f} ({time.time()-t0:.0f}s)")
    pd.DataFrame({"variable": ["intercept"] + MAIN,
                  "bw_spatial": list(np.ravel(mgt.bw_ts)),
                  "tau_temporal": list(np.ravel(mgt.taus))}
                 ).to_csv(os.path.join(OUT, f"bandwidths_{dv}_mgtwr.csv"), index=False)

    # 로컬 계수 저장 (MGTWR, MGWR)
    for tag, mres in (("MGTWR", mgt), ("MGWR", mgwr)):
        cols = ["intercept"] + MAIN
        bet = pd.DataFrame(mres.betas, columns=[f"b_{c}" for c in cols])
        tv = getattr(mres, "t_values", None)
        out_df = pd.concat([df[["sgg_cd", "sgg_nm", "year"]].reset_index(drop=True), bet], axis=1)
        if tv is not None:
            out_df = pd.concat([out_df, pd.DataFrame(tv, columns=[f"t_{c}" for c in cols])], axis=1)
        out_df.to_csv(os.path.join(OUT, f"local_coefs_{dv}_{tag}.csv"),
                      index=False, encoding="utf-8-sig")

    pd.DataFrame(rows).to_csv(os.path.join(OUT, "model_comparison.csv"), index=False)

log("ALL DONE")
