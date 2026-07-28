# -*- coding: utf-8 -*-
"""GTWR tau(시공간 스케일 비) 민감도: tau를 고정값으로 바꿔가며 AICc 변화 확인.
   tau가 탐색 상한에 붙는 문제의 해석 근거 마련 (03 완료 후 실행)."""
import os, time
import numpy as np
import pandas as pd

BASE = r"C:\Users\User\vibe_coding\obesity_platform\obesity_MGTWR"
OUT = os.path.join(BASE, "output")
MAIN = ["welfare_rate", "single_hh", "divorce_rate", "log_pop_density",
        "youth_net_mig", "doctors", "apt_ratio"]

df = pd.read_csv(os.path.join(OUT, "master_panel_2015_2023.csv"))
df = df.sort_values(["sgg_cd", "year"]).reset_index(drop=True)
coords = df[["cx_km", "cy_km"]].to_numpy(float)
tarr = df[["year"]].to_numpy(float)

def z(a):
    a = np.asarray(a, float)
    return (a - a.mean(0)) / a.std(0)

Xz = z(df[MAIN].to_numpy(float))
yz = z(df[["ob"]].to_numpy(float))

from mgtwr.sel import SearchGTWRParameter
from mgtwr.model import GTWR

rows = []
for tau in (10, 50, 100, 300, 1000, 3000, 10000):
    t0 = time.time()
    # tau 고정: tau_min=tau_max=tau 로 bw만 탐색
    sel = SearchGTWRParameter(coords, tarr, Xz, yz, kernel="bisquare",
                              fixed=False, thread=10)
    bw, tau_hat = sel.search(tau_min=tau, tau_max=tau + 0.01, verbose=False)
    res = GTWR(coords, tarr, Xz, yz, bw, tau_hat, kernel="bisquare",
               fixed=False, thread=10).fit()
    rows.append(dict(tau=tau, bw=bw, aicc=res.aicc, R2=res.R2, adj_R2=res.adj_R2))
    print(f"tau={tau:>6} bw={bw:>7} aicc={res.aicc:.1f} R2={res.R2:.4f} "
          f"({time.time()-t0:.0f}s)", flush=True)

pd.DataFrame(rows).to_csv(os.path.join(OUT, "tau_sensitivity_ob.csv"), index=False)
print("saved tau_sensitivity_ob.csv")
