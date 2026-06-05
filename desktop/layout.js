// SDACS Desktop — 순수(테스트 가능) 윈도우 배치 계산 로직.
// Electron 런타임 없이 단위 테스트할 수 있도록 main.js에서 분리한다.
'use strict';

// 여러 윈도우를 타일 배치할 bounds 배열을 계산한다.
//
// displays : Electron `screen.getAllDisplays()` 형태 — [{ workArea: {x,y,width,height} }, ...]
// count    : 배치할 윈도우 개수 (>=1)
// mode     : 'horizontal' | 'vertical' (단일 모니터 분할 방향, 기본 horizontal)
//
// 규칙:
//  - 모니터 수 >= 윈도우 수: 각 윈도우를 개별 모니터의 작업영역 전체에 배치(다중 모니터 자동 분산).
//  - 그 외: 첫 모니터 작업영역을 윈도우 수만큼 균등 분할.
//
// 반환: [{x,y,width,height}, ...] (길이 count)
function computeTileBounds(displays, count, mode) {
  if (!Array.isArray(displays) || displays.length === 0) {
    throw new Error('displays must be a non-empty array');
  }
  if (!Number.isInteger(count) || count < 1) {
    throw new Error('count must be a positive integer');
  }

  // 다중 모니터: 윈도우마다 전용 모니터 전체 배치
  if (displays.length >= count) {
    return displays.slice(0, count).map((d) => ({
      x: d.workArea.x,
      y: d.workArea.y,
      width: d.workArea.width,
      height: d.workArea.height,
    }));
  }

  // 단일(또는 부족한) 모니터: 첫 모니터 작업영역 균등 분할
  // (나머지 픽셀은 마지막 타일이 흡수해 작업영역을 빈틈없이 덮는다)
  const area = displays[0].workArea;
  return Array.from({ length: count }, (_, i) => {
    const isLast = i === count - 1;
    if (mode === 'vertical') {
      const h = Math.floor(area.height / count);
      return {
        x: area.x,
        y: area.y + h * i,
        width: area.width,
        height: isLast ? area.height - h * i : h,
      };
    }
    const w = Math.floor(area.width / count);
    return {
      x: area.x + w * i,
      y: area.y,
      width: isLast ? area.width - w * i : w,
      height: area.height,
    };
  });
}

module.exports = { computeTileBounds };
