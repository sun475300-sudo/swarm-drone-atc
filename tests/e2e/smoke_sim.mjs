// SDACS 웹 시뮬레이터 헤드리스 스모크 테스트
// _sdacs API로 각 뷰/토글/선택/리플레이/리포트를 결정적으로 검증한다.
// 로컬:  SIM_URL=http://localhost:8123/swarm_3d_simulator.html node tests/e2e/smoke_sim.mjs
// CI:    python http.server로 서빙 후 동일 실행.

let _pw;
try {
  _pw = await import('playwright');
} catch {
  _pw = await import('/opt/node22/lib/node_modules/playwright/index.js');
}
const chromium = _pw.chromium || _pw.default?.chromium;

const URL = process.env.SIM_URL || 'http://localhost:8123/swarm_3d_simulator.html';
const fails = [];
const ok = (cond, name) => { console.log(`${cond ? 'PASS' : 'FAIL'}  ${name}`); if (!cond) fails.push(name); };

const browser = await chromium.launch({
  headless: true,
  args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader',
    '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--ignore-certificate-errors'],
});
const ctx = await browser.newContext({ viewport: { width: 1400, height: 800 }, ignoreHTTPSErrors: true });
const page = await ctx.newPage();
const pageErrors = [];
page.on('pageerror', e => pageErrors.push(e.message));

try {
  await page.goto(URL, { waitUntil: 'load', timeout: 60000 });
  await page.waitForFunction(() => !!window._sdacs, { timeout: 45000 });

  // 1. 앱 부팅 + 드론 스폰
  const droneCount = await page.evaluate(() => window._sdacs.droneCount);
  ok(droneCount > 0, `드론 스폰 (${droneCount}대)`);

  // 2. 시뮬 시작 → 공중 드론 발생
  await page.evaluate(() => window._sdacs.selectScenario('route_conflict'));
  await page.waitForTimeout(400);
  await page.evaluate(() => window._sdacs.startSim());
  await page.waitForTimeout(12000);
  const airborne = await page.evaluate(() => window._sdacs.airborne);
  ok(airborne > 0, `이륙/비행 (${airborne}대 공중)`);

  // 2b. 외부 탐지·식별 (조류·비협조)
  const dni = await page.evaluate(() => window._sdacs.dni);
  ok(dni.detected > 0 && dni.identified > 0, `외부 탐지·식별 (탐지 ${dni.detected}/식별 ${dni.identified}/조류 ${dni.birds})`);

  // 3. 드론 선택 + 상세 조회
  const selId = await page.evaluate(() => window._sdacs.selectDrone(0));
  const sel = await page.evaluate(() => window._sdacs.getSelected());
  ok(!!selId && !!sel && sel.id === selId, `드론 선택 (${selId})`);

  // 4. 호버 툴팁
  const hovId = await page.evaluate(() => window._sdacs.hoverDrone(1));
  ok(!!hovId, `호버 툴팁 (${hovId})`);

  // 5. 분석 뷰 토글
  const av = await page.evaluate(() => window._sdacs.setAnalysisView(true));
  ok(av === true, '분석 뷰 ON');
  await page.evaluate(() => window._sdacs.setAnalysisView(false));

  // 6. 리플레이 레코더 + 시크
  const frames = await page.evaluate(() => window._sdacs.replayFrames);
  ok(frames > 5, `리플레이 레코더 (${frames} 프레임)`);
  const seekIdx = await page.evaluate(() => window._sdacs.replaySeek(0));
  ok(seekIdx === 0, '리플레이 시크(0)');
  await page.evaluate(() => window._sdacs.goLive());

  // 7. 리포트 PNG 생성
  const durl = await page.evaluate(async () => await window._sdacs.reportDataURL());
  ok(typeof durl === 'string' && durl.startsWith('data:image/png') && durl.length > 5000, '리포트 PNG 생성');

  // 8. 대규모 InstancedMesh 모드 (1000대)
  await page.evaluate(() => window._sdacs.selectScenario('mega_swarm_1k'));
  await page.evaluate(() => window._sdacs.startSim());
  await page.waitForTimeout(2500);
  const mega = await page.evaluate(() => ({ n: window._sdacs.droneCount, mode: window._sdacs.megaMode, inst: window._sdacs.instanceCount }));
  ok(mega.n === 1000 && mega.mode === true && mega.inst > 0, `대규모 InstancedMesh (${mega.n}대, inst=${mega.inst})`);

  // 8b. B6 성능 측정 API — 1000대 megaMode에서 draw call이 드론 수보다 적어야(InstancedMesh 효과 증명)
  await page.waitForTimeout(1200);
  const perf = await page.evaluate(() => window._sdacs.perf);
  ok(perf && perf.drones === 1000 && perf.megaMode === true && perf.drawCalls > 0 && perf.drawCalls < perf.drones && Number.isFinite(perf.fps) && perf.visibleInstances > 0,
    `B6 성능 측정 (DC=${perf.drawCalls} < 1000대, fps=${perf.fps}, vis=${perf.visibleInstances})`);

  // 8d. B2 대규모 CPA 충돌예측 복원 — 1k megaMode에서 공간해시로 충돌쌍 탐지(프리즈/에러 없이)
  const conflict = await page.evaluate(() => ({ pairs: window._sdacs.conflictPairs, mega: window._sdacs.megaMode, n: window._sdacs.droneCount }));
  ok(conflict.mega === true && conflict.n === 1000 && Number.isFinite(conflict.pairs) && conflict.pairs >= 0,
    `B2 대규모 CPA 충돌쌍 (${conflict.pairs}쌍 @1000대 megaMode)`);

  // 8c. B4 다중 선택 — 여러 드론 선택 후 집계 패널 동작
  await page.evaluate(() => window._sdacs.selectScenario('route_conflict'));
  await page.waitForTimeout(400);
  const multiN = await page.evaluate(() => window._sdacs.multiSelect([0, 1, 2, 3]));
  const multiList = await page.evaluate(() => window._sdacs.multiSelection);
  ok(multiN === 4 && multiList.length === 4, `B4 다중 선택 (${multiN}대: ${multiList.join(',')})`);
  await page.evaluate(() => window._sdacs.clearMulti());
  const cleared = await page.evaluate(() => window._sdacs.multiSelection.length);
  ok(cleared === 0, 'B4 다중 선택 해제');

  // 9. 페이지 런타임 에러 없음
  ok(pageErrors.length === 0, `런타임 에러 0건${pageErrors.length ? ' → ' + pageErrors.join(' | ') : ''}`);
} catch (e) {
  ok(false, '예외: ' + e.message);
} finally {
  await browser.close();
}

if (fails.length) {
  console.error(`\n❌ 스모크 테스트 실패 ${fails.length}건: ${fails.join(', ')}`);
  process.exit(1);
}
console.log('\n✅ 스모크 테스트 전체 통과');
