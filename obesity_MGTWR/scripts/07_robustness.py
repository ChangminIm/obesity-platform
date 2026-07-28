# -*- coding: utf-8 -*-
"""Phase 4-2: 강건성 (GTWR 수준 — MGTWR 재추정은 시간상 생략, 방향성 검증 목적)
   M0 기준 / M1 +재정자립도 / M2 아파트→노후주택 교체 / M3 +걷기(2017-23 축소)
   산출: output/robustness_gtwr.csv"""
import os, time
import numpy as np
import pandas as pd

BASE = r"C:\Users\User\vibe_coding\obesity_platform\obesity_MGTWR"
OUT = os.path.join(BASE, "output")
MAIN = ["welfare_rate", "single_hh", "divorce_rate", "log_pop_density",
        "youth_net_mig", "doctors", "apt_ratio"]
SPECS = {
    "M0_baseline": (MAIN, range(2015, 2024)),
    "M1_fiscal": (MAIN + ["fiscal_indep"], range(2015, 2024)),
    "M2_oldhousing": ([v if v != "apt_ratio" else "old_housing" for v in MAIN],
                      range(2015, 2024)),
    "M3_walk": (MAIN + ["walk"], range(2017, 2024)),
}

df = pd.read_csv(os.path.join(OUT, "master_panel_2015_2023.csv"),
                 dtype={"sgg_cd": str})
from mgtwr.sel import SearchGTWRParameter
from mgtwr.model import GTWR

rows = []
for dv in ("ob", "ow"):
    for spec, (vars_, years) in SPECS.items():
        sub = df[df.year.isin(years)][["sgg_cd", "year", "cx_km", "cy_km", dv] + vars_].dropna()
        sub = sub.sort_values(["sgg_cd", "year"])
        coords = sub[["cx_km", "cy_km"]].to_numpy(float)
        tarr = sub[["year"]].to_numpy(float)
        z = lambda a: (a - a.mean(0)) / a.std(0)
        Xz = z(sub[vars_].to_numpy(float))
        yz = z(sub[[dv]].to_numpy(float))
        t0 = time.time()
        sel = SearchGTWRParameter(coords, tarr, Xz, yz, kernel="bisquare",
                                  fixed=False, thread=10)
        bw, tau = sel.search(tau_max=300, verbose=False)
        res = GTWR(coords, tarr, Xz, yz, bw, tau, kernel="bisquare",
                   fixed=False, thread=10).fit()
        for j, v in enumerate(["intercept"] + vars_):
            b = res.betas[:, j]
            t = res.betas[:, j] / res.bse[:, j]
            rows.append(dict(dv=dv, spec=spec, n=len(sub),
                             n_sgg=sub.sgg_cd.nunique(), variable=v,
                             mean_beta=b.mean(), pct_pos=100 * (b > 0).mean(),
                             pct_sig_pos=100 * ((t > 1.96)).mean(),
                             pct_sig_neg=100 * ((t < -1.96)).mean(),
                             aicc=res.aicc, R2=res.R2, bw=bw, tau=tau))
        print(f"{dv} {spec} n={len(sub)} bw={bw} tau={tau} "
              f"aicc={res.aicc:.1f} R2={res.R2:.3f} ({time.time()-t0:.0f}s)",
              flush=True)

pd.DataFrame(rows).to_csv(os.path.join(OUT, "robustness_gtwr.csv"), index=False)
print("ROBUSTNESS DONE")
