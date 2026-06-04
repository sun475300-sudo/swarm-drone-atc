"""P744 폐쇄망(MIL/L4) 모드 검증."""
from __future__ import annotations

from src.closed_net.airgap_mode import (
    AirGapPolicy,
    _ip_in_cidrs,
    audit_config,
    check_url,
    is_internal_host,
    make_offline_policy_for_military,
)


def test_localhost_is_internal() -> None:
    p = AirGapPolicy()
    assert is_internal_host("localhost", p)
    assert is_internal_host("127.0.0.1", p)


def test_rfc1918_cidrs() -> None:
    """RFC1918 사설 IP 범위."""
    p = AirGapPolicy()
    assert _ip_in_cidrs("10.0.0.5", p.allowed_cidrs)
    assert _ip_in_cidrs("192.168.1.1", p.allowed_cidrs)
    assert _ip_in_cidrs("172.16.5.10", p.allowed_cidrs)
    assert not _ip_in_cidrs("8.8.8.8", p.allowed_cidrs)


def test_check_url_external_blocked() -> None:
    p = AirGapPolicy()
    ok, msg = check_url("https://fonts.googleapis.com/css", p)
    assert ok is False
    assert "외부" in msg or "차단" in msg


def test_check_url_file_scheme_allowed() -> None:
    p = AirGapPolicy()
    ok, msg = check_url("file:///vendor/three.module.js", p)
    assert ok is True


def test_check_url_invalid_scheme_blocked() -> None:
    p = AirGapPolicy()
    ok, _ = check_url("ftp://example.com/file", p)
    assert ok is False


def test_audit_detects_external_domain() -> None:
    """설정 안 외부 도메인 감사."""
    p = AirGapPolicy()
    cfg = {
        "fonts": "https://fonts.googleapis.com/css",
        "api": {"endpoint": "https://k-utm.molit.go.kr/api"},
        "nested": {"list": ["https://cdn.jsdelivr.net/three.js"]},
    }
    violations = audit_config(cfg, p)
    assert len(violations) >= 2
    flat = " ".join(violations)
    assert "googleapis" in flat
    assert "jsdelivr" in flat


def test_military_policy() -> None:
    p = make_offline_policy_for_military()
    assert "sdacs.mil.local" in p.allowed_hosts
    assert p.block_external_ntp
    assert p.block_external_dns
    assert p.require_offline_fonts


def test_internal_mil_hostname_allowed() -> None:
    p = make_offline_policy_for_military()
    assert is_internal_host("sdacs.mil.local", p)
