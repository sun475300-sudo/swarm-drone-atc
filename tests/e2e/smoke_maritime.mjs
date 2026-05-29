// 해양 소형선 감지 시뮬레이터 헤드리스 스모크 테스트
// _mds API로 스폰/탐지/식별/정확도/시나리오/무에러를 결정적으로 검증한다.
// 로컬:  SIM_URL=http://localhost:8123/maritime_detection_simulator.html node tests/e2e/smoke_maritime.mjs
// CI:    python http.server로 서빙 후 동일 실행.

let _pw;
try {
  _pw = await import('playwright');
} catch {
  _pw = await import('/opt/node22/lib/node_modules/playwright/index.js');
}
const chromium = _pw.chromium || _pw.default?.chromium;

const URL = process.env.SIM_URL || 'http://localhost:8123/maritime_detection_simulator.html';
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
  await page.waitForFunction(() => !!window._mds, { timeout: 45000 });

  // 1. 앱 부팅 + 소형선 스폰
  const total = await page.evaluate(() => window._mds.total);
  ok(total > 0, `소형선 스폰 (${total}척)`);

  // 2. 레이더/AIS 탐지 — 애니메이션 루프가 돌며 탐지 누적
  await page.evaluate(() => window._mds.start());
  await page.waitForFunction(() => window._mds.detected > 0, { timeout: 20000 }).catch(() => {});
  const detected = await page.evaluate(() => window._mds.detected);
  ok(detected > 0, `탐지 (${detected}척 탐지)`);

  // 3. 식별 (AIS 협조 즉시 + 비협조 분류)
  await page.waitForFunction(() => window._mds.identified > 0, { timeout: 20000 }).catch(() => {});
  const identified = await page.evaluate(() => window._mds.identified);
  ok(identified > 0, `식별 (${identified}척 식별)`);

  // 4. 식별 정확도 KPI 정상 범위
  const acc = await page.evaluate(() => window._mds.accuracy);
  ok(Number.isFinite(acc) && acc >= 0 && acc <= 100, `식별 정확도 (${acc.toFixed(1)}%)`);

  // 5. CPA/TCPA 경보 필드 정상
  const cpa = await page.evaluate(() => window._mds.cpaWarn);
  ok(Number.isFinite(cpa) && cpa >= 0, `CPA 경보 카운터 (${cpa})`);

  // 6. 시나리오 전환 (비협조 침입)
  await page.evaluate(() => window._mds.scenario('intrusion'));
  await page.waitForTimeout(800);
  const intrTotal = await page.evaluate(() => window._mds.total);
  ok(intrTotal > 0, `시나리오 전환·재스폰 (intrusion ${intrTotal}척)`);

  // 7. 혼잡 항만 시나리오 — 더 많은 표적
  await page.evaluate(() => window._mds.scenario('busy'));
  await page.waitForTimeout(800);
  const busyTotal = await page.evaluate(() => window._mds.total);
  ok(busyTotal > 0, `혼잡 항만 시나리오 (${busyTotal}척)`);

  // 8. 페이지 런타임 에러 없음
  ok(pageErrors.length === 0, `런타임 에러 0건${pageErrors.length ? ' → ' + pageErrors.join(' | ') : ''}`);
} catch (e) {
  ok(false, '예외: ' + e.message);
} finally {
  await browser.close();
}

if (fails.length) {
  console.error(`\n❌ 해양 스모크 테스트 실패 ${fails.length}건: ${fails.join(', ')}`);
  process.exit(1);
}
console.log('\n✅ 해양 스모크 테스트 전체 통과');
