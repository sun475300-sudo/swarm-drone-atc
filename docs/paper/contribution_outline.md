# SDACS 논문 기여 후보 outline (P701)

**목적**: IROS 2026 / AIAA SciTech 2027 투고용 기여 포인트 3개 후보 정제.  
**작성**: 2026-06-03. P707 초안 작성 전 지도교수 컨펌 대상 문서.

---

## 후보 비교

| 항목 | C1: APF+CBS 하이브리드 | C2: Voronoi 동적 공역 | C3: DnI 식별 정확도 모델 |
|---|---|---|---|
| **핵심 아이디어** | 단기 회피(APF) + 중장기 계획(CBS) 계층적 하이브리드 + 풍속 인지 자동 모드 전환 | 드론 밀도·임무 우선순위 기반 Voronoi 셀 실시간 재분할로 데드락 완화 | 협조/비협조 외부 객체 식별 시 거리·조도·기상에 따른 클래스별 정확도 모델 + 오분류 보정 |
| **Novelty** | • 풍속 >10 m/s 시 `APF_PARAMS_WINDY` 자동 전환<br>• CBS replan 트리거 = APF 충돌 지속 N tick<br>• 5계층 안전망 통합 | • Lloyd 알고리즘 + Voronoi 셀 변경 시 계획 핸드오버 프로토콜<br>• 우선순위 가중 분할 (EMERGENCY > DELIVERY) | • Confusion matrix를 거리·조도 함수로 파라미터화<br>• Bayesian 업데이트로 시간 누적 정확도 향상 |
| **벤치마크 대상** | ORCA·VO·단일 CBS | 정적 sector·KD-tree 분할 | 단순 임계 기반 분류 |
| **주요 메트릭** | NMR · MSD · AU · FT | RTF · 데드락률 · 핸드오버 지연 | 식별 정확도 · F1 · ROC AUC |
| **예상 개선폭** | NMR -25%, MSD +18% (P706 사전 결과) | 데드락 -40%, RTF -15% | 정확도 +12pp |
| **재현성 패키지** | ✅ P703-705 완비 | ⚠ Voronoi 적용 전후 시나리오 추가 필요 | ⚠ 외부 객체 시나리오 시드 5종 추가 |
| **실기 검증 의존** | SITL로 충분 | SITL로 충분 | 실 카메라 SDK 필요(P735) |
| **구현 완성도** | ✅ main 머지 완료 | ⚠ 핸드오버 프로토콜 일부 미구현 | ✅ 모델 + 모의 평가 완료 |
| **학회 적합도** | IROS·ICRA·AAMAS | IROS·CDC·ACC | IROS·ICRA·RA-L |
| **데드라인 적합** | ✅ IROS 2026 (1월) 가능 | ⚠ 추가 실험 2주 필요 | ⚠ 실 카메라 데이터 필요 |

---

## 권장 우선순위

1. **C1 (APF+CBS 하이브리드)** — Primary contribution
   - 이미 P703-P706으로 재현성 + 비교 실험 완료
   - 학회 핏 좋고 데드라인 안전
   - SDACS의 "5계층 안전망" 시스템 기여를 자연스럽게 elevate

2. **C2 (Voronoi 동적 공역)** — Secondary contribution
   - C1의 hand-in-hand 보완 메커니즘으로 포지셔닝
   - 핸드오버 프로토콜 + 추가 시나리오로 2주 내 완성 가능
   - "system contribution" 측면에서 평가자에게 어필

3. **C3 (DnI 정확도 모델)** — Discussion 또는 별도 short paper
   - 실 카메라 데이터 의존 → 본 논문에선 모의 평가만
   - RA-L letter 또는 IROS workshop short paper로 분리 권장

---

## 논문 제목 후보

1. **SDACS: A Hybrid APF-CBS Architecture for Robust Swarm-Drone Airspace Control under Wind Disturbances**
2. **Layered Safety Net for Urban UAS Traffic Management: Bridging Reactive Avoidance and Conflict-Based Planning**
3. **Voronoi-Augmented Hybrid Avoidance for Heterogeneous Drone Swarms in Disturbed Airspace**

---

## §-Outline (IROS 2026 양식, 6 pages)

- **§1 Introduction** (~0.5p) — UAM·UTM 배경, 기존 ORCA/CBS 한계, 본 논문 기여 3가지 (C1+C2+C3 요약)
- **§2 Related Work** (~1p) — ORCA/VO/CBS/Voronoi/Sector + 본 연구 차별점 (P702 출력 인용)
- **§3 Method** (~1.5p)
  - 3.1 5-Layer Safety Net 시스템 개요
  - 3.2 Wind-Aware APF (APF_PARAMS_WINDY 자동 전환)
  - 3.3 CBS replan Trigger = APF persistent conflict N tick
  - 3.4 (Optional) Voronoi 핸드오버 프로토콜
- **§4 Experiments** (~1.5p)
  - 4.1 시나리오 (P703 dataset 10종 + 3개 baseline)
  - 4.2 메트릭 (P705 NMR/MSD/PE/MS/FT/AU/RID_CR/RTF)
  - 4.3 결과 (P706 결과 표 + ablation: w/o wind-aware, w/o CBS, w/o APF)
- **§5 Discussion** (~1p) — 한계 (실기 부재), 향후 (P736 RL, P740 디지털 트윈)
- **§6 Conclusion** (~0.5p)
- **References** (~30편)

---

## 결정 항목 (지도교수 컨펌 필요)

- [ ] **타겟 학회/저널**: IROS 2026 vs AIAA SciTech 2027 vs RA-L
- [ ] **기여 범위**: C1 단독 vs C1+C2 통합
- [ ] **공동 저자**: 본인 + 지도교수 + 캡스톤 팀원
- [ ] **데드라인 확정**: IROS 2026 = 2026-01-15 추정 → P707-P709 일정 backward 계산

---

## 다음 단계

1. 본 문서를 지도교수께 공유 → 1주 내 컨펌
2. P702 서베이 시작 (Zotero 라이브러리 `sdacs-survey` 생성)
3. SP2에서 P707 §1-§3 LaTeX 초안 작성
