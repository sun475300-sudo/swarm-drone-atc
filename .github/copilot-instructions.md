# SDACS Copilot Instructions

## Polyglot Implementation Policy

- 신규 기능 구현 시 Python 단독 구현을 기본으로 하지 말고, 아래 기준에 따라 다중 언어 보완안을 함께 고려한다.
- 성능/시스템 경로: Rust, C++, Go 우선 검토.
- 실시간 UI/프로토콜/대시보드: TypeScript 우선 검토.
- 모바일/클라이언트 UX: Swift, Kotlin, Dart 우선 검토.
- 데이터/통계/실험 분석: R, Julia 우선 검토.
- 분산/신뢰성/운영 자동화: Go, Shell, SQL, Proto(gRPC) 우선 검토.

## Delivery Rule

- 각 Phase 완료 시 README의 Multi-Language 섹션 및 Changelog에 반영한다.
- Python 모듈만 추가한 경우에도 "향후 다중 언어 확장 포인트"를 최소 1개 이상 기록한다.
- 테스트는 Python 중심으로 유지하되, 다중 언어 모듈은 인터페이스/프로토콜 계약(예: proto, json schema) 기준으로 검증한다.
