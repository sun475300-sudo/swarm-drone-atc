#!/usr/bin/env bash
# (옵션) 오프라인 실행용 three.js 로컬 벤더링.
# swarm_3d_simulator.html이 기본적으로 unpkg CDN에서 three.js를 받으므로
# 인터넷 없이 실행하려면 이 스크립트로 three.js를 vendor/three/에 내려받은 뒤
# 아래 안내대로 importmap을 로컬 경로로 교체하세요.
set -euo pipefail
VER="0.162.0"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/vendor/three"
mkdir -p "$DEST/addons/controls"

base="https://unpkg.com/three@${VER}"
echo "three.js ${VER} 벤더링 → $DEST"
curl -fsSL "$base/build/three.module.js" -o "$DEST/three.module.js"
curl -fsSL "$base/examples/jsm/controls/OrbitControls.js" -o "$DEST/addons/controls/OrbitControls.js"

cat <<EOF

✅ 완료: vendor/three/ 에 three.js 저장됨.

오프라인 실행하려면 swarm_3d_simulator.html의 importmap을 다음으로 교체하세요:

  <script type="importmap">
  {
    "imports": {
      "three": "./vendor/three/three.module.js",
      "three/addons/": "./vendor/three/addons/"
    }
  }
  </script>

그 후 'python3 scripts/serve.py' 로 인터넷 없이 실행 가능합니다.
EOF
