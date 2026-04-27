# Security Policy / 보안 정책

## Supported Versions

This project is a Mokpo National University capstone design project. The latest
`main` branch is the only actively supported line.

| Version | Supported |
|---------|-----------|
| Phase 660+ (current) | ✅ |
| Phase 600-659 | ⚠️ Best-effort |
| Phase < 600 | ❌ Unsupported |

## Reporting a Vulnerability / 취약점 신고

학술 프로젝트이지만, 다음의 경우는 책임 있는 신고를 부탁드립니다.

If you believe you have discovered a security vulnerability, please email
**sun475300@gmail.com** with:

1. A clear description of the vulnerability
2. Steps to reproduce (or proof-of-concept)
3. Affected components (Layer 1-4, modules, scenarios)
4. Suggested mitigation if any

We will acknowledge receipt within 7 days and aim to provide a remediation
timeline within 14 days.

## Out of Scope

- Issues only reproducible against retired phases (< Phase 600)
- Performance / DoS findings against simulation runs (intended workload)
- Known limitations documented in `docs/AUDIT_2026-04-20.md`
- Vulnerabilities in archived directories (`archive/`)

## Disclosure Practice

We follow coordinated disclosure. Please refrain from public disclosure until a
fix is in `main` or an explicit advisory is issued. For academic / research
disclosure, this project welcomes coordinated publication after the fix lands.
