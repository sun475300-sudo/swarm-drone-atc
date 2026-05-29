#!/bin/bash
# SDACS 시뮬레이터 — macOS 원클릭 런처.
# Finder에서 더블클릭하면 로컬 서버를 띄우고 브라우저를 자동으로 엽니다.
# (최초 1회: 우클릭 > 열기 로 Gatekeeper 허용이 필요할 수 있습니다.)

# 심볼릭 링크(예: 데스크톱 별칭)로 실행돼도 실제 스크립트 위치로 이동.
SOURCE="${BASH_SOURCE[0]:-$0}"
while [ -h "$SOURCE" ]; do
  DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [ "${SOURCE#/}" = "$SOURCE" ] && SOURCE="$DIR/$SOURCE"
done
cd "$(cd -P "$(dirname "$SOURCE")" && pwd)" || exit 1

echo "============================================================"
echo "  SDACS 3D 시뮬레이터를 시작합니다..."
echo "============================================================"

if command -v python3 >/dev/null 2>&1; then
  python3 scripts/serve.py "$@"
elif command -v python >/dev/null 2>&1; then
  python scripts/serve.py "$@"
else
  echo "[오류] Python을 찾을 수 없습니다."
  echo "       https://www.python.org/downloads/ 에서 설치 후 다시 실행하세요."
  read -r -p "엔터를 누르면 종료합니다..."
fi
