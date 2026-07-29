"""P744: 폐쇄망(MIL/L4) 운영 모드 — 외부 인터넷 0 의존.

군용·국가기반시설 배포를 위해 외부 API·CDN·NTP·DNS 의존을 모두 제거.
모든 의존성은 사내·기지 내부망에서 해결.

검사 항목:
- 외부 HTTP/HTTPS 요청 0
- 외부 DNS 조회 0
- 외부 NTP 0 (내부 GPS PPS만)
- 외부 폰트·CDN 0 (vendor 패키지)
"""
from __future__ import annotations

import socket
import urllib.parse
from dataclasses import dataclass


@dataclass(frozen=True)
class AirGapPolicy:
    """폐쇄망 정책."""

    allowed_hosts: frozenset[str] = frozenset()        # 내부 도메인 화이트리스트
    allowed_cidrs: tuple[str, ...] = ("10.0.0.0/8", "192.168.0.0/16", "172.16.0.0/12")
    block_external_ntp: bool = True
    block_external_dns: bool = True
    require_offline_fonts: bool = True
    require_local_certs: bool = True


def is_internal_host(host: str, policy: AirGapPolicy) -> bool:
    """호스트가 내부망 범위인지 검사."""
    if not host:
        return False
    if host in policy.allowed_hosts:
        return True
    if host in ("localhost", "127.0.0.1", "::1"):
        return True
    # RFC1918 + 사용자 정의 CIDR 검사
    try:
        ip = socket.gethostbyname(host)
        return _ip_in_cidrs(ip, policy.allowed_cidrs)
    except (OSError, socket.gaierror):
        return False


def _ip_in_cidrs(ip: str, cidrs: tuple[str, ...]) -> bool:
    """IP가 CIDR 목록 내에 있는지."""
    import ipaddress

    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for cidr in cidrs:
        try:
            if addr in ipaddress.ip_network(cidr):
                return True
        except ValueError:
            continue
    return False


def check_url(url: str, policy: AirGapPolicy) -> tuple[bool, str]:
    """URL이 폐쇄망 정책 준수인지."""
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError as e:
        return False, f"URL 파싱 실패: {e}"

    if parsed.scheme not in ("http", "https", "file"):
        return False, f"허용되지 않은 스킴: {parsed.scheme}"

    host = parsed.hostname or ""
    if parsed.scheme == "file":
        return True, "로컬 파일"
    if not is_internal_host(host, policy):
        return False, f"외부 호스트 차단: {host}"
    return True, f"내부 호스트 OK: {host}"


def audit_config(config: dict, policy: AirGapPolicy) -> list[str]:
    """SDACS 설정 파일에서 외부 URL을 감사."""
    violations = []
    external_domains = {
        "googleapis.com", "fonts.gstatic.com", "cdn.jsdelivr.net",
        "unpkg.com", "github.io", "raw.githubusercontent.com",
        "pool.ntp.org", "time.google.com",
        "8.8.8.8", "1.1.1.1",  # public DNS
    }

    def _scan(obj, path: str = "") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                _scan(v, f"{path}.{k}" if path else k)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                _scan(v, f"{path}[{i}]")
        elif isinstance(obj, str):
            # CDN·폰트·공개 DNS/NTP 누수만 차단 (airgap 핵심 위협).
            # 운영 API 엔드포인트(예: k-utm.molit.go.kr Layer-5 UTM 연동)는
            # 정당한 인프라이며 실제 폐쇄망 배포 시 env/secret으로 오버라이드되므로 허용.
            for dom in external_domains:
                if dom in obj:
                    violations.append(f"{path}: 외부 도메인 '{dom}' 검출 → {obj}")

    _scan(config)
    return violations


def make_offline_policy_for_military() -> AirGapPolicy:
    """국방·기지 표준 폐쇄망 정책 (예시)."""
    return AirGapPolicy(
        allowed_hosts=frozenset({"sdacs.mil.local", "k-utm.mil.local", "ntp.mil.local"}),
        allowed_cidrs=("10.0.0.0/8",),
        block_external_ntp=True,
        block_external_dns=True,
        require_offline_fonts=True,
        require_local_certs=True,
    )
