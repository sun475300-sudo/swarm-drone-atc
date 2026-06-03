#!/bin/bash
# SDACS 시뮬레이터 — Linux 원클릭 런처.
# 파일 관리자에서 더블클릭(실행) 하거나 터미널에서 ./run_simulator.sh 로 실행합니다.

# 심볼릭 링크로 실행돼도 실제 스크립트 위치로 이동.
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
  echo "[오류] Python을 찾을 수 없습니다. python3를 설치 후 다시 실행하세요."
  read -r -p "엔터를 누르면 종료합니다..."
fi
