# SDACS Good First Issue Queue

This queue defines small contributions with concrete ownership boundaries and
verification. Open an issue with the **Good First Issue proposal** form and
reference one ID. Maintainers should create the `good first issue` and
`mentoring` labels before publishing the queue.

| ID | Area | Task | Primary files | Acceptance check |
|---|---|---|---|---|
| GFI-01 | JS core | Add CPA typed-array input coverage | `packages/core/test/core.test.js` | `npm run test:core` |
| GFI-02 | JS core | Add APF windy interpolation boundary tests at 6 and 12 m/s | `packages/core/test/core.test.js` | Exact parameter assertions pass |
| GFI-03 | JS core | Add a browser ESM usage example | `packages/core/examples/` | Example imports without a bundler |
| GFI-04 | Packaging | Enforce a 10 kB compressed budget for `@sdacs/core` | `scripts/`, package workflow | CI fails above the documented budget |
| GFI-05 | Typing | Replace five high-use `_sdacs` `any` declarations with interfaces | `docs/sdacs.d.ts` | API extraction check remains green |
| GFI-06 | Telemetry | Add one valid and three invalid telemetry JSON fixtures | `tests/fixtures/telemetry/` | JSON Schema validation test passes |
| GFI-07 | Scenario | Add a minimal `.sdacs-scenario` example | `docs/examples/` | `simulation/scenario_schema.py` accepts it |
| GFI-08 | Scenario | Improve one Korean schema error message | `simulation/scenario_schema.py` | Existing and new error-path tests pass |
| GFI-09 | Federation | Document federation query parameters and topology offsets | `docs/` | Links to the two-instance E2E |
| GFI-10 | Federation | Add disconnected-peer status recovery coverage | `tests/e2e/federation_two_instance.mjs` | Ghost layer hides after peer shutdown |
| GFI-11 | Web UI | Add a keyboard-focus test for simulator controls | `tests/e2e/` | Playwright tab-order assertion passes |
| GFI-12 | Web UI | Add an accessible label to one icon-only control group | `swarm_3d_simulator.html` | No visual regression; selector test passes |
| GFI-13 | Documentation | Audit ten README links with the link checker | `README.md`, `scripts/` | All selected links return or resolve |
| GFI-14 | Documentation | Synchronize one missing section in `README.en.md` | `README.en.md` | Heading parity test passes |
| GFI-15 | Benchmark | Document one benchmark scenario manifest field-by-field | `benchmarks/scenarios/` | YAML remains valid |
| GFI-16 | Plugin SDK | Add a deterministic weather-source example plugin | `examples/plugins/` | Plugin registry loads and executes it |
| GFI-17 | Plugin SDK | Add a KPI widget example plugin | `examples/plugins/` | Plugin contract test passes |
| GFI-18 | Plugin SDK | Add a custom drone-profile example plugin | `examples/plugins/` | Validation rejects one malformed profile |
| GFI-19 | CI | Add package artifact names to workflow summaries | `.github/workflows/` | Summary contains wheel and npm tarball names |
| GFI-20 | PWA | Document LIVE/federation behavior while offline | `docs/`, `sdacs-sw.js` | Offline smoke keeps DEMO mode usable |

## Maintainer workflow

1. Confirm the item is still unclaimed and relevant to `main`.
2. Open one GitHub issue per ID using the issue form.
3. Add a mentor, affected component label, and an expected test command.
4. Close or rewrite stale items instead of keeping an inaccurate beginner queue.
