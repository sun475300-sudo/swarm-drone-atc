"""src/storage/timescale.py — P714 TimescaleDB 이력 저장 레이어.

PostgreSQL + TimescaleDB를 asyncpg로 비동기 연결하여
드론 원격측정·충돌 이벤트·임무 로그를 영속 저장한다.

사용 예시:
    storage = TimescaleStorage(dsn="postgresql://user:pw@localhost:5432/sdacs")
    await storage.connect()

    await storage.insert_telemetry(
        drone_id="drone_01",
        lat=37.123, lon=127.456, alt=50.0,
        heading=270.0, speed=12.5, battery_pct=88, status="flying",
    )
    rows = await storage.query_telemetry_range("drone_01", start, end)
    await storage.close()
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

try:
    import asyncpg
    from asyncpg import Pool, Record
    _ASYNCPG_AVAILABLE = True
except ImportError:  # pragma: no cover — asyncpg 미설치 환경 대비 fallback
    _ASYNCPG_AVAILABLE = False
    Pool = Any  # 타입 힌트 전용 별칭
    Record = Any

LOGGER = logging.getLogger("sdacs.storage.timescale")

# 기본 DSN — 환경변수 우선, 없으면 로컬 개발용 기본값
_DEFAULT_DSN = os.environ.get(
    "DATABASE_URL",
    "postgresql://sdacs:sdacs@localhost:5432/sdacs",
)

# 커넥션 풀 크기 설정
_POOL_MIN_SIZE = 2
_POOL_MAX_SIZE = 10


class TimescaleStorage:
    """PostgreSQL/TimescaleDB 비동기 스토리지 클라이언트.

    수명 주기:
        await storage.connect()   → 연결 풀 생성
        await storage.close()     → 연결 풀 해제
        async with TimescaleStorage.from_env() as storage:  → 컨텍스트 관리
    """

    def __init__(self, dsn: str = _DEFAULT_DSN) -> None:
        # DSN: postgresql://user:password@host:port/dbname 형식
        self._dsn = dsn
        self._pool: Pool | None = None

    # ------------------------------------------------------------------
    # 연결 관리
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """연결 풀을 생성한다. 서버 시작 시 한 번만 호출."""
        if not _ASYNCPG_AVAILABLE:
            raise RuntimeError(
                "asyncpg 패키지가 필요합니다: pip install asyncpg"
            )
        self._pool = await asyncpg.create_pool(
            dsn=self._dsn,
            min_size=_POOL_MIN_SIZE,
            max_size=_POOL_MAX_SIZE,
        )
        LOGGER.info("TimescaleDB 연결 풀 생성 완료 (min=%d, max=%d)", _POOL_MIN_SIZE, _POOL_MAX_SIZE)

    async def close(self) -> None:
        """연결 풀을 해제한다. 서버 종료 시 호출."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            LOGGER.info("TimescaleDB 연결 풀 해제 완료")

    async def __aenter__(self) -> TimescaleStorage:
        await self.connect()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    @classmethod
    def from_env(cls) -> TimescaleStorage:
        """환경변수 DATABASE_URL에서 DSN을 읽어 인스턴스를 생성한다."""
        return cls(dsn=_DEFAULT_DSN)

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------

    def _require_pool(self) -> Pool:
        """풀이 초기화되었는지 확인하고 반환한다."""
        if self._pool is None:
            raise RuntimeError(
                "스토리지가 연결되지 않았습니다. await storage.connect()를 먼저 호출하세요."
            )
        return self._pool

    # ------------------------------------------------------------------
    # drone_telemetry 헬퍼
    # ------------------------------------------------------------------

    async def insert_telemetry(
        self,
        *,
        drone_id: str,
        lat: float,
        lon: float,
        alt: float,
        heading: float,
        speed: float,
        battery_pct: int,
        status: str,
        time: datetime | None = None,
    ) -> None:
        """드론 원격측정 레코드 1건을 drone_telemetry에 삽입한다.

        Args:
            drone_id:    드론 식별자
            lat:         위도 (degrees)
            lon:         경도 (degrees)
            alt:         고도 (meters AGL)
            heading:     방위각 (0–360 degrees)
            speed:       속도 (m/s)
            battery_pct: 배터리 잔량 (0–100)
            status:      드론 상태 문자열
            time:        타임스탬프 (None이면 현재 UTC 시각)
        """
        pool = self._require_pool()
        ts = time if time is not None else datetime.now(timezone.utc)

        await pool.execute(
            """
            INSERT INTO drone_telemetry
                (time, drone_id, lat, lon, alt, heading, speed, battery_pct, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            ts, drone_id, lat, lon, alt, heading, speed, battery_pct, status,
        )

    async def query_telemetry_range(
        self,
        drone_id: str,
        start: datetime,
        end: datetime,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """특정 드론의 시간 범위 내 원격측정 데이터를 반환한다.

        Args:
            drone_id: 조회할 드론 식별자
            start:    조회 시작 시각 (UTC)
            end:      조회 종료 시각 (UTC)
            limit:    최대 반환 레코드 수 (기본 1000)

        Returns:
            시간 오름차순 정렬된 원격측정 레코드 리스트
        """
        pool = self._require_pool()
        rows = await pool.fetch(
            """
            SELECT time, drone_id, lat, lon, alt, heading, speed, battery_pct, status
            FROM drone_telemetry
            WHERE drone_id = $1
              AND time >= $2
              AND time <= $3
            ORDER BY time ASC
            LIMIT $4
            """,
            drone_id, start, end, limit,
        )
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # conflict_events 헬퍼
    # ------------------------------------------------------------------

    async def insert_conflict(
        self,
        *,
        drone_a_id: str,
        drone_b_id: str,
        separation_m: float,
        resolved: bool = False,
        resolution_type: str | None = None,
        time: datetime | None = None,
    ) -> int:
        """공역 충돌 이벤트를 conflict_events에 삽입하고 생성된 id를 반환한다.

        Args:
            drone_a_id:      첫 번째 드론 식별자
            drone_b_id:      두 번째 드론 식별자
            separation_m:    감지 시점의 드론 간 거리 (m)
            resolved:        충돌 해결 여부
            resolution_type: 해결 방법 ('avoidance', 'atc_command', 등)
            time:            이벤트 시각 (None이면 현재 UTC)

        Returns:
            생성된 레코드의 id
        """
        pool = self._require_pool()
        ts = time if time is not None else datetime.now(timezone.utc)

        row = await pool.fetchrow(
            """
            INSERT INTO conflict_events
                (time, drone_a_id, drone_b_id, separation_m, resolved, resolution_type)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            ts, drone_a_id, drone_b_id, separation_m, resolved, resolution_type,
        )
        return row["id"]

    async def query_conflicts_last_n(
        self,
        n: int = 100,
        drone_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """최근 n개의 충돌 이벤트를 반환한다.

        Args:
            n:        반환할 최대 레코드 수 (기본 100)
            drone_id: 특정 드론 필터 (None이면 전체 드론)

        Returns:
            시간 내림차순 정렬된 충돌 이벤트 리스트
        """
        pool = self._require_pool()

        if drone_id is not None:
            # 특정 드론이 drone_a 또는 drone_b로 관여한 충돌만 조회
            rows = await pool.fetch(
                """
                SELECT id, time, drone_a_id, drone_b_id,
                       separation_m, resolved, resolution_type
                FROM conflict_events
                WHERE drone_a_id = $1 OR drone_b_id = $1
                ORDER BY time DESC
                LIMIT $2
                """,
                drone_id, n,
            )
        else:
            rows = await pool.fetch(
                """
                SELECT id, time, drone_a_id, drone_b_id,
                       separation_m, resolved, resolution_type
                FROM conflict_events
                ORDER BY time DESC
                LIMIT $1
                """,
                n,
            )

        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # mission_log 헬퍼
    # ------------------------------------------------------------------

    async def insert_mission_event(
        self,
        *,
        drone_id: str,
        mission_id: str,
        event_type: str,
        payload: dict[str, Any] | None = None,
        time: datetime | None = None,
    ) -> int:
        """임무 이벤트를 mission_log에 삽입하고 생성된 id를 반환한다.

        Args:
            drone_id:   드론 식별자
            mission_id: 임무 식별자
            event_type: 이벤트 유형 ('start', 'waypoint_reached', 'complete', 'abort')
            payload:    이벤트별 추가 데이터 (JSONB로 저장)
            time:       이벤트 시각 (None이면 현재 UTC)

        Returns:
            생성된 레코드의 id
        """
        pool = self._require_pool()
        ts = time if time is not None else datetime.now(timezone.utc)
        # asyncpg는 dict를 JSONB에 직접 바인딩할 수 없으므로 JSON 문자열로 변환
        payload_json = json.dumps(payload) if payload is not None else None

        row = await pool.fetchrow(
            """
            INSERT INTO mission_log
                (time, drone_id, mission_id, event_type, payload)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            RETURNING id
            """,
            ts, drone_id, mission_id, event_type, payload_json,
        )
        return row["id"]

    async def query_mission_events(
        self,
        mission_id: str,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """특정 임무의 이벤트 로그를 시간 오름차순으로 반환한다.

        Args:
            mission_id: 조회할 임무 식별자
            limit:      최대 반환 레코드 수 (기본 500)

        Returns:
            시간 오름차순 정렬된 임무 이벤트 리스트
        """
        pool = self._require_pool()
        rows = await pool.fetch(
            """
            SELECT id, time, drone_id, mission_id, event_type, payload
            FROM mission_log
            WHERE mission_id = $1
            ORDER BY time ASC
            LIMIT $2
            """,
            mission_id, limit,
        )
        # payload를 Python dict로 역직렬화
        result: list[dict[str, Any]] = []
        for r in rows:
            record = dict(r)
            if isinstance(record.get("payload"), str):
                record["payload"] = json.loads(record["payload"])
            result.append(record)
        return result
