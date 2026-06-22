# 영유아 소아비만 시군구 EHSA 웹지도 — 통합 안내

## 산출 파일
- `ehsa.html` — 자체완결 인터랙티브 지도(데이터·경계 내장, 단독 실행 가능)
- `ehsa_data.js` — 동일 데이터 별도 모듈(선택)
- `region_*_ehsa.png` (12) — 권역별 EHSA 정지도(ESRI 심볼)
- `region_*_giyear.png` / `.gif` — 권역별 연도별 Gi\* z 격자/애니메이션
- `권역별_EHSA결과.csv` — 646행, 12권역 z·EHSA 라벨(utf-8-sig)
- `권역별_EHSA_shp.zip` — 11개 권역 shp(GIS용)
- `EHSA_symbol_test.png` — ESRI 심볼 범례 시트
- `권역별_중재지역_보고서.md` — 분석 보고서

## 웹지도 사용
- 탭 12개: 전국·수도권·서울·충청권·전북·전남·전라권·경북·경남·경상권·강원·제주
- 모드: 연도별 핫스팟(Gi\*) / EHSA 패턴
- 지표: 비만율(ob)·과체중이상율(ow)·비만 아동수(cnt)
- 연도 슬라이더 2012–2024
- EHSA 라벨 영문(Persistent/Intensifying/New/Consecutive/Sporadic/Oscillating/Diminishing/Historical Hot·Cold, No Pattern)
- 색상: ESRI EHSA 표준 색

## 분석 방법
- ArcGIS EHSA 방식(공간시간 Gi\*, NTS=1, Neighborhood Time Step) + 섬연결 가중 + FDR(전역 BH q=0.10)
- 전국 = 전국 기준, 권역 = 권역 내 비교

## GitHub Pages(ChangminIm/wonju-school-medical-map) 통합
1. `ehsa.html`을 저장소 루트에 복사
2. `index.html` 카드 목록에 링크 추가:
   ```html
   <a class="map-card" href="ehsa.html">영유아 소아비만 시군구 분석</a>
   ```
3. 내장 경계는 좌표 단순화(coarse)본 — 고해상도가 필요하면:
   - `bnd_sigungu` shp를 EPSG:4326로 변환
   - 속성 `sgg`(=SIGUNGU_CD)·`name` 포함 GeoJSON 생성 → `ehsa_geo.js`로 저장
   - HTML의 `EHSA_GEO` 상수 교체(또는 별도 로드)
4. 한국어 UI·건국대 그린 테마·CartoDB Positron NoLabels 기존 톤 유지

## 주의
- 규모(cnt) 지도는 인구 분포와 강하게 연동 → "위험 증가"가 아닌 "대상자 규모"로 해석
- 균질 권역(전라권 등)은 권역 내 No Pattern 다수 — 권역 간 비교는 전국 탭 참고
- ArcGIS와 큰 틀 동일, 섬은 본 분석이 개선, 내륙 경계 라벨은 재구현 미세차 가능
