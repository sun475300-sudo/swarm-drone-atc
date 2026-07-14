# ICRA 2027 Compression Plan — 8 pages → 6+1

**Source draft:** `PAPER_DRAFT.md` (SciTech 8-page target, ~6,500 words)
**Target:** ICRA 2027 CFP standard — **6 pages of content + 1 page of references**
**Deadline:** 2026-09-15 (D-76 from 2026-07-01 baseline)

---

## 1. Compression axes

We need to shave **≈ 2 pages of content** (~25 % of body). Three axes:

| Axis | Where the fat is | How much can go |
|------|------------------|-----------------|
| **A. Related Work** (§2) | 30-ref narrative currently ~1.0 p | → 0.5 p, use compact table + hard citations |
| **B. System architecture** (§3) | Figure + pseudocode + interaction table = 1.5 p | → 1.0 p, keep Fig. 1, cut pseudocode to 8 lines |
| **C. Contribution 3 cross-domain** (§5.6) | Currently 1/2 column | → **cut entirely**, spin off as separate AAAI/RA-L short paper |
| **D. Discussion** (§6) | 1.0 p | → 0.7 p, merge threats-to-validity into §5 caveats |
| **E. Reproducibility Docker block** | 0.3 p | → 0.1 p, move to appendix / repo README |

Together: A −0.5 + B −0.5 + C −0.5 + D −0.3 + E −0.2 = **−2.0 pages ✓**

---

## 2. Section-by-section diff

### §1 Abstract + Introduction (1.0 p → **0.8 p**)
- Cut the "regulatory conformance is future work" hedge; make it a first-class claim.
- Trim contribution bullets to 3× 1-line.

### §2 Related Work (1.0 p → **0.5 p**)
- Replace 4-bucket narrative with **Table 2** (30 refs × 5-col: year / author / venue / bucket / one-liner claim).
- Retain 3-sentence positioning paragraph.
- Move BibTeX to `refs/` (already there).

### §3 System (1.5 p → **1.0 p**)
- **Keep:** Fig. 1 architecture diagram (essential).
- **Cut:** the 20-line Python pseudocode in §3.2 — replace with a **6-line
  algorithmic sketch** in LaTeX `\begin{algorithmic}`.
- **Cut:** §3.3 layer interaction table — merge into a single "Failure
  modes and how each layer helps" paragraph.

### §4 Benchmark (1.0 p → **0.8 p**)
- Keep Table 1 (10-row scenario roster).
- Cut the "docker run" one-liner (move to §7 or README) — save a paragraph.

### §5 Experiments and Results (2.0 p, **unchanged**)
- Non-negotiable — 3 figures + 2 tables + Welch t-test all live here.

### §5.6 Cross-domain (0.5 p → **cut entirely**)
- Contribution 3 goes to a **separate RA-L short paper** on the SC2
  bridge.
- Add a 1-line "we also observe the same compositional pattern in a
  sister project [ref]" in §6 Discussion instead.

### §6 Discussion (1.0 p → **0.7 p**)
- Merge "Threats to validity" into a single tighter paragraph.
- Fold "Ethics & dual-use" into a one-liner in §7 Conclusion.

### §7 Conclusion + Future Work (0.3 p, **unchanged**)

### References (1.0 p, **unchanged**)
- ICRA gives us the full 7th page for refs — 30 entries fit comfortably.

---

## 3. Decisions locked

| # | Decision | Locked |
|---|----------|--------|
| D1 | Cut Contribution 3 (cross-domain) from ICRA | ✅ locked here |
| D2 | Keep 3 figures (Fig. 2/3/4). No new figures. | ✅ locked |
| D3 | Move Docker reproducibility to appendix in supplementary | ✅ locked |
| D4 | Related-Work becomes a table, not prose | ✅ locked |
| D5 | Single-author submission (advisor as ack, not co-author) | 🟡 needs advisor sign-off |

---

## 4. Section budget (final)

| § | Section | Pages |
|---|---------|-------|
| 1 | Abstract + Introduction | 0.8 |
| 2 | Related Work (table + 3-sentence positioning) | 0.5 |
| 3 | System Architecture (Fig. 1 + short algo) | 1.0 |
| 4 | Benchmark Suite (Table 1) | 0.8 |
| 5 | Experiments + Results (Fig. 2/3/4 + Table 2) | 2.0 |
| 6 | Discussion | 0.7 |
| 7 | Conclusion | 0.2 |
| — | **Content total** | **6.0** ✓ |
| 8 | References (30 refs) | 1.0 |
| — | **Grand total** | **7.0** ✓ |

---

## 5. Execution schedule (from 2026-07-01)

| Sub-sprint | Dates | Milestone |
|------------|-------|-----------|
| S1 (W1) | 07-01 → 07-07 | This plan + advisor sign-off on D5 |
| S2 (W2) | 07-08 → 07-14 | Table 2 (30-ref compact) drafted; §3.2 algo boxed |
| S3 (W3) | 07-15 → 07-21 | Contribution 3 spun off to RA-L branch (`ral-sc2-bridge` in repo) |
| S4 (W4) | 07-22 → 07-28 | First 6+1 page draft compiled in ICRA LaTeX template |
| S5 (W5) | 07-29 → 08-04 | Advisor round 1 |
| S6 (W6) | 08-05 → 08-11 | Revision |
| S7 (W7) | 08-12 → 08-18 | Internal reviews × 3 |
| S8 (W8) | 08-19 → 08-25 | Freeze, arXiv preprint |
| S9 (W9) | 08-26 → 09-15 | Submit + buffer |

---

## 6. Risks

| Risk | Prob | Mitigation |
|------|------|-----------|
| Advisor rejects D5 (single-author) | 30% | Two-author sub, add ack for lab members |
| ICRA CFP page rules change (rare) | 5% | Recheck 08-01 |
| Contribution 3 spin-off delayed | 40% | RA-L submission is independent, no hard tie |
| Fig 4 log-scale suddenly looks unimpressive | 20% | Re-run with N=500 stress scenario |
| Overlength on first compile | 60% | 0.2p buffer built into schedule |

---

*Locked 2026-07-11. Reopen if ICRA 2027 CFP changes materially.*
