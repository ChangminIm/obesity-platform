# -*- coding: utf-8 -*-
"""스토리맵 빌드: 경량 GeoJSON + MGTWR 로컬 계수 + 요약 수치를
   storymap/template.html 의 /*__DATA__*/ 자리에 주입 → storymap/index.html"""
import json, os
import numpy as np
import pandas as pd
import geopandas as gpd

BASE = r"C:\Users\User\vibe_coding\obesity_platform\obesity_MGTWR"
OUT = os.path.join(BASE, "output")
SM = os.path.join(BASE, "storymap")
ALLV = ["intercept", "welfare_rate", "single_hh", "divorce_rate",
        "log_pop_density", "youth_net_mig", "doctors", "apt_ratio"]
YEARS = list(range(2015, 2024))

# ---- geometry: dissolve 캐시 → simplify → WGS84 → 좌표 4자리 반올림 ----
gdf = gpd.read_file(os.path.join(BASE, "data", "sgg229_dissolved.gpkg")).set_index("sgg229")
gdf["geometry"] = gdf.geometry.simplify(400)
gdf = gdf.to_crs(4326)
gj = json.loads(gdf.reset_index().to_json())

def rnd(obj):
    if isinstance(obj, list):
        return [rnd(o) for o in obj]
    if isinstance(obj, float):
        return round(obj, 4)
    return obj

for f in gj["features"]:
    f["geometry"]["coordinates"] = rnd(f["geometry"]["coordinates"])
    f["properties"] = {"sgg": f["properties"]["sgg229"]}
print("geojson size(KB):", len(json.dumps(gj)) // 1024)

# ---- 이름 ----
panel = pd.read_csv(os.path.join(OUT, "master_panel_2015_2023.csv"), dtype={"sgg_cd": str})
names = panel.drop_duplicates("sgg_cd").set_index("sgg_cd")["sgg_nm"].to_dict()

# ---- 로컬 계수/유의성 ----
coef, sig, vmax, tcrit = {}, {}, {}, {}
for dv in ("ob", "ow"):
    co = pd.read_csv(os.path.join(OUT, f"local_coefs_{dv}_MGTWR.csv"), dtype={"sgg_cd": str})
    tc = pd.read_csv(os.path.join(OUT, f"enp_critical_t_{dv}.csv")).set_index("variable")
    coef[dv], sig[dv], vmax[dv] = {}, {}, {}
    tcrit[dv] = {v: round(float(tc.loc[v, "t_crit"]), 2) for v in ALLV}
    for v in ALLV:
        pb = co.pivot_table(index="sgg_cd", columns="year", values="b_" + v)[YEARS]
        pt = co.pivot_table(index="sgg_cd", columns="year", values="t_" + v)[YEARS]
        vmax[dv][v] = round(float(max(abs(np.percentile(pb.values, 2)),
                                      abs(np.percentile(pb.values, 98)))), 3)
        coef[dv][v] = {s: [round(float(x), 3) for x in row]
                       for s, row in pb.iterrows()}
        thr = tc.loc[v, "t_crit"]
        sig[dv][v] = {s: "".join("1" if abs(x) >= thr else "0" for x in row)
                      for s, row in pt.iterrows()}

# ---- 전국 추이 (2012-2024) ----
dep = pd.read_csv(os.path.join(OUT, "dependent_vars_2012_2024.csv"))
g = dep.groupby("year")
trend = {"years": sorted(dep.year.unique().tolist()),
         "ob": [round(float(x), 2) for x in g.obesity_rate.mean()],
         "ow": [round(float(x), 2) for x in g.overweight_plus_rate.mean()],
         "cnt": [int(x) for x in g.obese_count.sum()]}

# ---- 절편(기저위험) 연도 추이 ----
inter = {}
for dv in ("ob", "ow"):
    co = pd.read_csv(os.path.join(OUT, f"local_coefs_{dv}_MGTWR.csv"))
    inter[dv] = [round(float(x), 3) for x in co.groupby("year")["b_intercept"].mean()]

# ---- 모델 비교 ----
mc = pd.read_csv(os.path.join(OUT, "model_comparison.csv"))
models = ["OLS", "GWR", "MGWR", "GTWR", "MGTWR"]
modelcmp = {dv: {"aicc": [round(float(mc[(mc.dv == dv) & (mc.model == m)].aicc.iloc[0]), 1)
                          for m in models],
                 "r2": [round(float(mc[(mc.dv == dv) & (mc.model == m)].R2.iloc[0]), 3)
                        for m in models]} for dv in ("ob", "ow")}

# ---- 코로나 Δ (ob) ----
cs = pd.read_csv(os.path.join(OUT, "covid_shift_ob.csv")).set_index("variable")
covid = {v: {"pre": round(float(cs.loc[v, "mean_pre"]), 3),
             "post": round(float(cs.loc[v, "mean_post"]), 3)}
         for v in ALLV}

# ---- 학술 버전용: bandwidth·tau, Moran's I, ENP ----
bwt = {}
for dv in ("ob", "ow"):
    b = pd.read_csv(os.path.join(OUT, f"bandwidths_{dv}_mgtwr.csv")).set_index("variable")
    e = pd.read_csv(os.path.join(OUT, f"enp_critical_t_{dv}.csv")).set_index("variable")
    bwt[dv] = {v: {"bw": round(float(b.loc[v, "bw_spatial"]), 1),
                   "tau": round(float(b.loc[v, "tau_temporal"]), 1),
                   "enp": round(float(e.loc[v, "ENP_j"]), 1),
                   "tcrit": round(float(e.loc[v, "t_crit"]), 2)} for v in ALLV}
moran = {dv: [round(float(mc[(mc.dv == dv) & (mc.model == m)].moran.iloc[0]), 3)
              for m in models] for dv in ("ob", "ow")}
adjr2 = {dv: [round(float(mc[(mc.dv == dv) & (mc.model == m)].adj_R2.iloc[0]), 3)
              for m in models] for dv in ("ob", "ow")}

DATA = dict(geo=gj, names=names, coef=coef, sig=sig, vmax=vmax, tcrit=tcrit,
            years=YEARS, vars=ALLV, trend=trend, inter=inter,
            modelcmp=modelcmp, covid=covid, models=models,
            bwt=bwt, moran=moran, adjr2=adjr2)
blob = json.dumps(DATA, ensure_ascii=False, separators=(",", ":"))
print("total data size(KB):", len(blob) // 1024)

for tpl_name, out_name in (("template.html", "index.html"),
                           ("academic_template.html", "academic.html")):
    p = os.path.join(SM, tpl_name)
    if not os.path.exists(p):
        continue
    tpl = open(p, encoding="utf-8").read()
    html = tpl.replace("/*__DATA__*/", "const DATA = " + blob + ";")
    with open(os.path.join(SM, out_name), "w", encoding="utf-8") as f:
        f.write(html)
    print("written storymap/" + out_name + ":", len(html) // 1024, "KB")
