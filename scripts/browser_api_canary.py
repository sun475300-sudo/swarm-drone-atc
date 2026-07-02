"""Phase 482 — 브라우저 API 폐기 감시 카나리 (Browser API Deprecation Canary).

WebGPU·WebXR·MediaRecorder·OffscreenCanvas·Web Worker 등 시뮬레이터가 의존하는
브라우저 API 의 *현재 가용성* 을 헤드리스 Chromium 으로 결정적으로 측정한다.

목적:
1. 브라우저 메이저 업그레이드 시 silent breakage 조기 탐지 (API 사라짐·시그니처 변경·정책 변경)
2. CI 게이트로 폐기 신호 자동 알림 (실패 시 마이그레이션 작업 트리거)
3. SDACS 가 의존하는 API 의 안정성 가시화 (실측 표 — `docs/standards/BROWSER_API_CANARY.md`)

사용:
    python scripts/browser_api_canary.py            # 측정 + 보고서 stdout
    python scripts/browser_api_canary.py --json     # JSON 출력 (CI 게이트용)
    python scripts/browser_api_canary.py --check    # 모든 필수 API 가용 시 exit 0, 누락 시 exit 1
    python scripts/browser_api_canary.py --required webgpu mediarecorder  # 특정 API 만 필수 지정

전제: pip install playwright && playwright install chromium

CI 게이트:
- 본 스크립트가 `--check` 로 실패하면 → 시뮬레이터 핵심 기능(GPU compute·녹화·worker) 회귀 위험
- 회피 가능 폐기(예: WebXR — 시뮬레이터 미사용)는 `OPTIONAL` 표시
"""
from __future__ import annotations

import argparse
import http.server
import json
import socketserver
import sys
import threading
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

# SDACS 시뮬레이터가 의존하는 API + 카나리 페이지 평가 스니펫
# 'required': True 면 본 API 누락 시 시뮬레이터 핵심 기능 회귀
API_PROBES: list[dict[str, Any]] = [
    {
        "id": "webgpu",
        "name": "WebGPU (GPU Compute Shader)",
        "required": True,
        "snippet": "!!navigator.gpu && typeof navigator.gpu.requestAdapter === 'function'",
        "used_by": "APF 힘 계산 GPU 가속 (_gpuDevice / dispatchGpuCompute)",
    },
    {
        "id": "webworker",
        "name": "Web Worker",
        "required": True,
        "snippet": "typeof Worker !== 'undefined'",
        "used_by": "APF 공간해시 CPU 폴백 (_apfWorker)",
    },
    {
        "id": "mediarecorder",
        "name": "MediaRecorder API",
        "required": True,
        "snippet": "typeof MediaRecorder !== 'undefined' && typeof MediaRecorder.isTypeSupported === 'function'",
        "used_by": "시네마틱 녹화 (cinRecorder, stopRecording)",
    },
    {
        "id": "offscreencanvas",
        "name": "OffscreenCanvas",
        "required": False,
        "snippet": "typeof OffscreenCanvas !== 'undefined'",
        "used_by": "(현재 미사용, 향후 worker 렌더링 후보)",
    },
    {
        "id": "webgl2",
        "name": "WebGL 2.0",
        "required": True,
        "snippet": "(() => { const c = document.createElement('canvas'); return !!c.getContext('webgl2'); })()",
        "used_by": "Three.js r162 렌더링 (InstancedMesh)",
    },
    {
        "id": "fetch",
        "name": "Fetch API",
        "required": True,
        "snippet": "typeof fetch === 'function'",
        "used_by": "vendor three.js 모듈 로딩",
    },
    {
        "id": "importmap",
        "name": "ES Module Import Maps",
        "required": True,
        "snippet": "(() => { const s = document.createElement('script'); s.type='importmap'; return s.type === 'importmap'; })()",
        "used_by": "<script type=\"importmap\"> Three.js 별칭",
    },
    {
        "id": "csp_meta",
        "name": "CSP via <meta http-equiv>",
        "required": True,
        "snippet": "typeof document.querySelector('meta[http-equiv=\"Content-Security-Policy\"]') !== 'undefined'",
        "used_by": "보안 6차 점검 CSP 헤더 (XSS 표면 축소)",
    },
    {
        "id": "structuredclone",
        "name": "structuredClone",
        "required": False,
        "snippet": "typeof structuredClone === 'function'",
        "used_by": "(미사용, 미래 후보)",
    },
    {
        "id": "abortcontroller",
        "name": "AbortController",
        "required": False,
        "snippet": "typeof AbortController !== 'undefined'",
        "used_by": "(미사용, fetch 취소 후보)",
    },
    {
        "id": "webxr",
        "name": "WebXR Device API",
        "required": False,
        "snippet": "!!navigator.xr && typeof navigator.xr.isSessionSupported === 'function'",
        "used_by": "(현재 미사용, Phase 81 Vision Pro 후보 — STELLAR)",
    },
    {
        "id": "broadcastchannel",
        "name": "BroadcastChannel",
        "required": False,
        "snippet": "typeof BroadcastChannel !== 'undefined'",
        "used_by": "(미사용, 다중 탭 동기 후보)",
    },
]


def measure_apis(sim_html: str = "swarm_3d_simulator.html") -> dict[str, Any]:
    """헤드리스 Chromium 으로 모든 API 가용성 측정.

    반환:
        {
            "browser": {"name": "Chromium", "version": "..."},
            "probes": [{"id": "webgpu", "available": True/False, ...}],
            "required_missing": ["..."],  # 필수인데 누락된 API id
            "summary": {"total": N, "available": M, "required": R, "required_available": RA},
        }
    """
    from playwright.sync_api import sync_playwright

    class _QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_a):
            pass

        def translate_path(self, path):
            import os

            rel = path.lstrip("/")
            return os.path.join(str(ROOT), rel)

    class _ReusableServer(socketserver.TCPServer):
        allow_reuse_address = True

    with _ReusableServer(("127.0.0.1", 0), _QuietHandler) as httpd:
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    args=[
                        "--no-sandbox",
                        "--use-gl=angle",
                        "--use-angle=swiftshader",
                        "--enable-unsafe-swiftshader",
                        "--enable-features=Vulkan,UseSkiaRenderer",
                    ]
                )
                ver = browser.version
                page = browser.new_page()
                page.goto(f"http://127.0.0.1:{port}/{sim_html}", wait_until="load", timeout=30000)
                # _sdacs 가 부팅된 후에 측정 (브라우저 환경 충분히 초기화)
                page.wait_for_function(
                    "() => window._sdacs && window._sdacs.droneCount > 0", timeout=15000
                )

                probes_out = []
                for probe in API_PROBES:
                    try:
                        available = bool(page.evaluate(f"() => {probe['snippet']}"))
                    except Exception as exc:  # noqa: BLE001
                        available = False
                        probe = {**probe, "error": str(exc)[:200]}
                    probes_out.append(
                        {
                            "id": probe["id"],
                            "name": probe["name"],
                            "required": probe["required"],
                            "available": available,
                            "used_by": probe["used_by"],
                        }
                    )
                browser.close()
        finally:
            httpd.shutdown()

    required_missing = [
        p["id"] for p in probes_out if p["required"] and not p["available"]
    ]
    summary = {
        "total": len(probes_out),
        "available": sum(1 for p in probes_out if p["available"]),
        "required": sum(1 for p in probes_out if p["required"]),
        "required_available": sum(
            1 for p in probes_out if p["required"] and p["available"]
        ),
    }
    return {
        "browser": {"name": "Chromium", "version": ver},
        "probes": probes_out,
        "required_missing": required_missing,
        "summary": summary,
    }


def render_report(data: dict[str, Any]) -> str:
    """결과를 사람이 읽기 좋은 표 형식으로."""
    lines = [
        f"# 🔭 SDACS 브라우저 API 카나리 (Phase 482)",
        f"",
        f"브라우저: **{data['browser']['name']} {data['browser']['version']}**",
        f"",
        f"## 측정 결과",
        f"",
        f"| API | 필수 | 가용 | 사용처 |",
        f"|---|:-:|:-:|---|",
    ]
    for p in data["probes"]:
        mark = "✅" if p["available"] else "❌"
        req = "🔒" if p["required"] else "—"
        lines.append(f"| {p['name']} | {req} | {mark} | {p['used_by']} |")

    s = data["summary"]
    lines += [
        f"",
        f"## 요약",
        f"",
        f"- 전체: **{s['available']}/{s['total']}** 가용",
        f"- 필수: **{s['required_available']}/{s['required']}** 가용",
    ]
    if data["required_missing"]:
        lines.append(
            f"- ⚠️ **필수 누락**: {', '.join(data['required_missing'])} — 마이그레이션 필요"
        )
    else:
        lines.append(f"- ✅ 필수 API 전부 가용 — 회귀 없음")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="JSON 출력 (CI 파싱용)")
    parser.add_argument(
        "--check",
        action="store_true",
        help="필수 API 누락 시 exit 1 (CI 게이트)",
    )
    parser.add_argument(
        "--required",
        nargs="*",
        default=None,
        help="추가로 필수 처리할 API id (기본은 API_PROBES required=True)",
    )
    parser.add_argument(
        "--sim",
        default="swarm_3d_simulator.html",
        help="대상 HTML (기본: 군집 ATC 시뮬레이터)",
    )
    args = parser.parse_args()

    data = measure_apis(sim_html=args.sim)

    # 추가 필수 지정 반영
    if args.required:
        extra = set(args.required)
        # required_missing 재계산
        data["required_missing"] = sorted(
            {
                p["id"]
                for p in data["probes"]
                if (p["required"] or p["id"] in extra) and not p["available"]
            }
        )

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(render_report(data))

    if args.check:
        return 1 if data["required_missing"] else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
