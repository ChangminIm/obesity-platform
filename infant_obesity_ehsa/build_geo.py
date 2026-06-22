# -*- coding: utf-8 -*-
"""index.html 의 EHSA_GEO 블록을 data/ 새 시군구 shp로 재생성.
- EPSG:4326, properties = {sgg(문자열·앞0유지), name}
- name 은 EHSA_DATA(전국 region) 의 코드->이름을 사용(코드체계 완전 일치 보장)
- 전국 252개 모두 포함, 단순화로 용량 관리
"""
import json, re, sys
import geopandas as gpd

HTML = 'index.html'
SHP = 'data/bnd_sigungu_00_2025_2Q.shp'
TOL = 60  # m, EPSG:5179 에서 단순화 허용오차
DEC = 4   # 좌표 소수자리(약 11m)

with open(HTML, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# --- EHSA_DATA 파싱 (line 98 = 'const EHSA_DATA = {...};') ---
def find_const_line(name):
    for i, l in enumerate(lines):
        if l.startswith('const %s = ' % name):
            return i
    raise SystemExit('not found: ' + name)

di = find_const_line('EHSA_DATA')
gi = find_const_line('EHSA_GEO')
data_txt = lines[di].split('= ', 1)[1].rstrip()
if data_txt.endswith(';'):
    data_txt = data_txt[:-1]
data = json.loads(data_txt)

# 전국 = unit 수가 가장 많은 region
nat_key = max(data['regions'], key=lambda k: len(data['regions'][k]['units']))
units = data['regions'][nat_key]['units']
code2name = {c: u['name'] for c, u in units.items()}
data_codes = set(code2name)
print('EHSA_DATA national region units:', len(data_codes))

# --- shp ---
g = gpd.read_file(SHP)  # SIGUNGU_CD / SIGUNGU_NM / geometry, EPSG:5179
g['sgg'] = g['SIGUNGU_CD'].astype(str).str.zfill(5)
shp_codes = set(g['sgg'])
print('shp features:', len(g), 'distinct codes:', len(shp_codes))
print('DATA - shp (missing geom):', sorted(data_codes - shp_codes))
print('shp - DATA (extra geom):', sorted(shp_codes - data_codes))

g = g.to_crs(4326)
g['geometry'] = g['geometry'].simplify(TOL / 111320.0, preserve_topology=True)

def rnd(o):
    if isinstance(o, (list, tuple)):
        return [rnd(x) for x in o]
    return round(o, DEC)

feats = []
for _, row in g.sort_values('sgg').iterrows():
    code = row['sgg']
    geom = row['geometry']
    if geom is None or geom.is_empty:
        print('WARN empty geom', code); continue
    gj = geom.__geo_interface__
    gj = {'type': gj['type'], 'coordinates': rnd(gj['coordinates'])}
    name = code2name.get(code) or row['SIGUNGU_NM']
    feats.append({'type': 'Feature',
                  'properties': {'sgg': code, 'name': name},
                  'geometry': gj})

print('features built:', len(feats))
fc = {'type': 'FeatureCollection', 'features': feats}
newline = 'const EHSA_GEO = ' + json.dumps(fc, ensure_ascii=False, separators=(',', ':')) + ';\n'
print('new EHSA_GEO bytes:', len(newline.encode('utf-8')))

if '--write' in sys.argv:
    lines[gi] = newline
    with open(HTML, 'w', encoding='utf-8', newline='') as f:
        f.writelines(lines)
    print('WROTE index.html')
else:
    print('(dry run; pass --write to apply)')
