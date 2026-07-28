# -*- coding: utf-8 -*-
"""독립변수 선별: 229개 시군구 × 2015-2023 패널 구축 후
   비만율(ob)·과체중이상율(ow)과의 상관 + VIF 진단"""
import csv, re, json, os
import numpy as np

BASE = r"C:\Users\User\vibe_coding\obesity_platform\obesity_MGTWR"
IV = os.path.join(BASE, "data", "독립변수", "독립변수")
YEARS = list(range(2015, 2024))

def dec(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp949", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")

def num(s):
    s = str(s).strip().replace(",", "")
    if s in ("", "-", "X", "..", "None"):
        return None
    try:
        return float(s)
    except ValueError:
        return None

# ---------- 종속변수: 252 -> 229 집계 ----------
src = open(os.path.join(BASE, "..", "infant_obesity_ehsa", "index.html"), encoding="utf-8").read()
data = json.loads(re.search(r"EHSA_DATA = (\{.*?\});", src, re.S).group(1))
years_all = data["years"]
units = data["regions"]["전국"]["units"]

# IV쪽 229개 코드 집합 (총인구.csv 기준)
rows = list(csv.reader(dec(os.path.join(IV, "총인구.csv")).splitlines()))
ci = rows[0].index("SIG_CD")
iv_codes = {r[ci].strip() for r in rows[1:] if len(r) > ci and r[ci].strip().isdigit()}

def parent(code):
    return code if code in iv_codes else code[:4] + "0"

# 수검아동수 역산: examined = cnt / (ob/100)
dv = {}  # (sgg229, year) -> [sum_obese, sum_ow, sum_examined, list_ob, list_ow]
name229 = {}
for code, u in units.items():
    p = parent(code)
    if p not in iv_codes:
        continue
    name229.setdefault(p, u["name"].split()[0] + "(" + u["sido"] + ")")
    for i, y in enumerate(years_all):
        if y not in YEARS:
            continue
        ob, ow, cnt = u["ob"][i], u["ow"][i], u["cnt"][i]
        if ob is None:
            continue
        key = (p, y)
        d = dv.setdefault(key, [0.0, 0.0, 0.0, [], []])
        d[3].append(ob); d[4].append(ow)
        if ob > 0 and cnt is not None:
            ex = cnt / (ob / 100.0)
            d[0] += cnt
            d[1] += ex * ow / 100.0
            d[2] += ex

panel = {}
for (p, y), d in dv.items():
    if d[2] > 0:
        panel[(p, y)] = {"ob": d[0] / d[2] * 100, "ow": d[1] / d[2] * 100}
    else:
        panel[(p, y)] = {"ob": float(np.mean(d[3])), "ow": float(np.mean(d[4]))}

# ---------- 독립변수 로더 ----------
def read_wide(fname, var):
    rows = list(csv.reader(dec(os.path.join(IV, fname)).splitlines()))
    hdr = rows[0]
    ci = [i for i, h in enumerate(hdr) if "SIG_CD" in h][0]
    ycols = {}
    for i, h in enumerate(hdr):
        m = re.search(r"(19|20)\d{2}", h)
        if m and i != ci:
            ycols[i] = int(m.group(0))
    out = {}
    for r in rows[1:]:
        if len(r) <= ci or not r[ci].strip().isdigit():
            continue
        sgg = r[ci].strip()
        for i, y in ycols.items():
            if y in YEARS and i < len(r):
                v = num(r[i])
                if v is not None:
                    out[(sgg, y, var)] = v
    return out

def read_long(fname, valcol, var, sggcol="SIG_CD", yearcol="year"):
    rows = list(csv.reader(dec(os.path.join(IV, fname)).splitlines()))
    hdr = [h.strip().strip('﻿"') for h in rows[0]]
    ci = [i for i, h in enumerate(hdr) if "SIG_CD" in h][0]
    yi = [i for i, h in enumerate(hdr) if h.lower() == yearcol][0]
    vi = [i for i, h in enumerate(hdr) if h == valcol][0]
    out = {}
    for r in rows[1:]:
        if len(r) <= max(ci, yi, vi):
            continue
        sgg, ys, v = r[ci].strip(), r[yi].strip(), num(r[vi])
        if sgg.isdigit() and ys.isdigit() and int(ys) in YEARS and v is not None:
            out[(sgg, int(ys), var)] = v
    return out

X = {}
X.update(read_wide("1인가구비율_시도_시_군_구__20260601233955.csv", "single_hh"))
X.update(read_wide("고령인구비율_시도_시_군_구__20260602000505.csv", "elderly_ratio"))
X.update(read_wide("Youth population ratio.csv", "youth_ratio"))
X.update(read_wide("청년순이동률_시도_시_군_구__20260602000955.csv", "youth_net_mig"))
X.update(read_wide("노후주택비율_시도_시_군_구__20260602222644.csv", "old_housing"))
X.update(read_wide("재정자립도_시도_시_군_구__20260602222141.csv", "fiscal_indep"))
X.update(read_wide("조이혼율_시도_시_군_구__20260602004921.csv", "divorce_rate"))
X.update(read_wide("인구_천명당_의료기관_종사_의사수_시도_시_군_구__20260602005957.csv", "doctors"))
X.update(read_wide("인구_십만명당_문화기반시설수_시도_시_군_구__20260521231451.csv", "cultural_fac"))
X.update(read_wide("독거노인가구비율_시도_시_군_구__20260521223730.csv", "lone_elderly"))
X.update(read_wide("Residentialarearatio.csv", "resid_area"))
X.update(read_wide("Commercialarearatio.csv", "comm_area"))
X.update(read_long("apt_ratio_final.csv", "apt_ratio", "apt_ratio"))
X.update(read_long("business_density_2014_2023.csv", "log_business_density", "log_biz_density"))
X.update(read_long("pop_density_panel.csv", "log_pop_density", "log_pop_density"))
X.update(read_long("foreign_ratio.csv", "foreign_ratio", "foreign_ratio"))
X.update(read_long("인구유입율.csv", "inflow_ratio", "inflow_ratio"))
for v in ("walk", "smoke", "drink"):
    X.update(read_long("걷기 실천율, 흡연율, 음주율.csv", v, v))

import openpyxl
ws = openpyxl.load_workbook(os.path.join(IV, "welfare_rate.xlsx"))["Sheet1"]
for r in ws.iter_rows(min_row=2, values_only=True):
    sgg, y, wr = str(r[1]), r[2], r[8]
    if y in YEARS and wr is not None:
        X[(sgg, int(y), "welfare_rate")] = float(wr)

VARS = ["welfare_rate", "fiscal_indep", "old_housing", "single_hh", "divorce_rate",
        "youth_ratio", "elderly_ratio", "lone_elderly", "youth_net_mig",
        "log_pop_density", "apt_ratio", "resid_area", "comm_area", "log_biz_density",
        "doctors", "cultural_fac", "foreign_ratio", "inflow_ratio",
        "walk", "smoke", "drink"]

# ---------- 매트릭스 구성 (pooled) ----------
def build(varlist, years):
    keys = [k for k in sorted(panel) if k[1] in years]
    rows_, used = [], []
    for (sgg, y) in keys:
        vals = [X.get((sgg, y, v)) for v in varlist]
        if all(v is not None for v in vals):
            rows_.append([panel[(sgg, y)]["ob"], panel[(sgg, y)]["ow"]] + vals)
            used.append((sgg, y))
    return np.array(rows_), used

def corr(a, b):
    return float(np.corrcoef(a, b)[0, 1])

# 개별 변수별 DV 상관
print("%-18s %6s %8s %8s" % ("var", "n", "r_ob", "r_ow"))
stats = {}
for v in VARS:
    yrs = YEARS if v not in ("walk", "smoke", "drink") else list(range(2017, 2024))
    M, _ = build([v], yrs)
    if len(M) == 0:
        continue
    stats[v] = (len(M), corr(M[:, 2], M[:, 0]), corr(M[:, 2], M[:, 1]))
    print("%-18s %6d %8.3f %8.3f" % (v, *stats[v]))

# 변수 간 상관행렬 (2015-2023 완비 변수만)
CORE = [v for v in VARS if v not in ("walk", "smoke", "drink")]
M, used = build(CORE, YEARS)
print("\npooled complete-case n =", len(M), " (시군구", len({u[0] for u in used}), ")")
C = np.corrcoef(M[:, 2:].T)
print("\n|r|>0.7 pairs:")
for i in range(len(CORE)):
    for j in range(i + 1, len(CORE)):
        if abs(C[i, j]) > 0.7:
            print("  %-16s %-16s %6.2f" % (CORE[i], CORE[j], C[i, j]))

def vif(Mx):
    out = []
    n, k = Mx.shape
    Z = (Mx - Mx.mean(0)) / Mx.std(0)
    for j in range(k):
        yv = Z[:, j]
        Xo = np.column_stack([np.ones(n), np.delete(Z, j, axis=1)])
        b, *_ = np.linalg.lstsq(Xo, yv, rcond=None)
        r2 = 1 - ((yv - Xo @ b) ** 2).sum() / ((yv - yv.mean()) ** 2).sum()
        out.append(1 / (1 - r2) if r2 < 1 else np.inf)
    return out

print("\nVIF (전체 18개 후보):")
for v, f in sorted(zip(CORE, vif(M[:, 2:])), key=lambda x: -x[1]):
    print("  %-16s %8.1f" % (v, f))
