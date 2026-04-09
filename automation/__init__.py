"""
SDACS 자동화 파이프라인
=====================
데이터 수집 → 가공 → 저장을 자동화하는 모듈 패키지.

모듈:
    collect_sim      — Monte Carlo 스윕 + 시나리오 벤치마크 실행/수집
    collect_external — 암호화폐 시세, 날씨, SC2 래더 외부 API 수집
    process          — 필터링, 통계 계산, 포맷 변환
    store            — 로컬 파일 / Google Drive / DB 동시 저장
    pipeline         — 전체 흐름 오케스트레이션, 오류 처리, 로깅
"""
