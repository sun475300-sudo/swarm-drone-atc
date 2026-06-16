"""ODYSSEY Phase 434 (Federation): HLC 통합 인과-안정(causal-stable) 배달.

Phase 432 메시 토폴로지(:class:`FederationMesh`)는 origin 의 사건을 멀티홉으로
*전파*하지만, 각 수신 인스턴스가 그것을 **어떤 순서로 처리(배달)** 해야 안전한지는
규정하지 않는다. 메시 플러딩에서는 같은 사건이 여러 경로로 도착하고(중복), 서로
다른 origin 의 사건이 뒤섞여 도착하므로, 순진하게 도착 순서대로 처리하면 인스턴스
마다 사건 순서가 어긋나 연합 결정(핸드오버·NOTAM·충돌 협상)이 불일치한다.

본 모듈은 Phase 431 하이브리드 논리 시계(HLC)를 메시 위에 결합해 **인과-안정 배달**
을 제공한다. 핵심은 *워터마크(low-water-mark) 안정 타임스탬프* 기법이다 —
CockroachDB 의 closed timestamp 와 동일한 발상으로, 각 출처(source)가 FIFO 로
**단조 증가하는** HLC 타임스탬프를 발행한다는 사실을 이용한다:

- 어떤 출처 s 의 최신 관측 HLC 가 ``T_s`` 이면, FIFO 단조성에 의해 s 는 앞으로
  ``T_s`` 보다 작은 사건을 결코 발행하지 않는다.
- 따라서 모든 알려진 출처에 대해 ``min_s T_s`` (워터마크) 이하인 버퍼 속 사건은
  **안정** 하다 — 그보다 앞선(작은) 사건이 미래에 새로 도착할 수 없다.
- 안정 사건만, 그것도 HLC **전순서** 로 정렬해 배달하면, 모든 인스턴스가 동일한
  결정적 순서로 사건을 처리한다(재현·감사 가능).

설계 원칙(인접 federation_* 모듈과 동일): 외부 네트워크·랜덤 0. 같은 (수신·broadcast)
호출 열은 항상 같은 배달 열을 만든다. 멀티홉 중복은 멱등 무시한다.
"""

from __future__ import annotations

from dataclasses import dataclass

from simulation.federation_hybrid_clock import HLCTimestamp
from simulation.federation_mesh import FederationMesh


@dataclass(frozen=True)
class FederationEvent:
    """한 연합 사건 — HLC 타임스탬프 + 불투명 페이로드(불변).

    출처(:pyattr:`source`)는 타임스탬프의 ``instance_id`` 다(HLC 가 이미 발행
    인스턴스를 담는다). 페이로드는 본 모듈이 해석하지 않는 임의 값이다.
    """

    timestamp: HLCTimestamp
    payload: object = None

    @property
    def source(self) -> str:
        """이 사건을 발행한 인스턴스 id(타임스탬프의 ``instance_id``)."""
        return self.timestamp.instance_id


class CausalDeliveryBuffer:
    """한 수신 인스턴스의 인과-안정 배달 버퍼(상태형·결정적).

    여러 출처로부터 HLC 스탬프 사건을 받아 버퍼링하고, 모든 알려진 출처의 진척이
    보장하는 *안정 워터마크* 이하의 사건만 HLC 전순서로 배달한다. 멀티홉으로 인한
    중복(또는 stale 재전송)은 출처별 단조 고점으로 멱등 무시한다.

    출처 집합(``sources``)을 주면 그 모든 출처가 1건 이상 보고할 때까지 워터마크가
    전진하지 않는다(아직 보고 안 한 출처가 더 작은 사건을 보낼 수 있으므로 보수적).
    주지 않으면 *관측된* 출처들만으로 워터마크를 잡는다(best-effort, 출처 집합을
    미리 알 수 없을 때).
    """

    def __init__(self, instance_id: str, sources: set[str] | None = None) -> None:
        if not instance_id:
            raise ValueError("instance_id가 비어 있음")
        self._instance_id = instance_id
        # 예상 출처 집합(주어지면 고정). 자기 자신은 출처가 아니다(지역 사건은
        # 버퍼를 거치지 않고 직접 처리하므로). None 이면 관측 출처로 best-effort.
        self._expected: frozenset[str] | None = (
            frozenset(sources) - {instance_id} if sources is not None else None
        )
        self._buffer: list[FederationEvent] = []
        self._source_high: dict[str, HLCTimestamp] = {}
        self._last_delivered: HLCTimestamp | None = None

    @property
    def instance_id(self) -> str:
        return self._instance_id

    def receive(self, event: FederationEvent) -> bool:
        """사건 1건을 버퍼에 받는다. 새로 받았으면 True, 중복/stale 이면 False.

        FIFO 단조성: 같은 출처의 사건은 전순서로 엄격 증가해야 한다. 출처의 현재
        고점 이하(``<=``)인 사건은 멀티홉 중복 또는 stale 재전송으로 보고 멱등
        무시한다. 자기 자신이 출처인 사건은 받지 않는다(지역 사건은 버퍼 우회).
        """
        if not isinstance(event, FederationEvent):
            raise TypeError("event는 FederationEvent여야 함")
        source = event.source
        if source == self._instance_id:
            raise ValueError("자기 자신이 출처인 사건은 버퍼에 받을 수 없음")
        if self._expected is not None and source not in self._expected:
            raise ValueError(f"예상 출처 집합에 없는 출처: {source!r}")
        prev = self._source_high.get(source)
        if prev is not None and event.timestamp <= prev:
            return False  # 중복 또는 stale → 멱등 무시
        self._source_high[source] = event.timestamp
        self._buffer.append(event)
        return True

    def _watermark(self) -> HLCTimestamp | None:
        """안정 워터마크 = 알려진 모든 출처의 최신 HLC 중 최소(전순서). 없으면 None.

        예상 출처 집합이 있으면 *모든* 예상 출처가 보고해야 하고, 하나라도 미보고면
        None(아무것도 안정이 아님). best-effort 모드는 관측 출처만으로 최소를 잡는다.
        """
        if self._expected is not None:
            if not self._expected:
                return None  # 예상 출처가 없으면 워터마크가 정의되지 않음
            if not self._expected <= self._source_high.keys():
                return None  # 미보고 출처가 있음 → 보수적으로 보류
            return min(self._source_high[s] for s in self._expected)
        if not self._source_high:
            return None
        return min(self._source_high.values())

    def deliverable(self) -> tuple[FederationEvent, ...]:
        """지금 배달 가능한(안정) 사건을 HLC 전순서로, 버퍼를 비우지 않고 반환한다."""
        watermark = self._watermark()
        if watermark is None:
            return ()
        ready = [e for e in self._buffer if e.timestamp <= watermark]
        ready.sort(key=lambda e: e.timestamp)
        return tuple(ready)

    def flush(self) -> tuple[FederationEvent, ...]:
        """안정 사건을 HLC 전순서로 배달하고 버퍼에서 제거한다.

        배달 열은 전순서로 단조 증가한다(직전 배달 고점보다 항상 큼). 반환 후
        버퍼에는 아직 안정이 아닌(워터마크 초과) 사건만 남는다.
        """
        watermark = self._watermark()
        if watermark is None:
            return ()
        # 워터마크로 직접 분할한다(객체 식별자에 의존하지 않음 → 불투명/비해시
        # 페이로드도 안전, 구조적 중복 재배달 불가). 안정분은 전순서 정렬해 배달.
        ready = tuple(
            sorted(
                (e for e in self._buffer if e.timestamp <= watermark),
                key=lambda e: e.timestamp,
            )
        )
        if not ready:
            return ()
        self._buffer = [e for e in self._buffer if e.timestamp > watermark]
        self._last_delivered = ready[-1].timestamp
        return ready

    def pending(self) -> tuple[FederationEvent, ...]:
        """아직 안정이 아니라 보류 중인 버퍼 사건을 HLC 전순서로 반환한다."""
        watermark = self._watermark()
        held = (
            list(self._buffer)
            if watermark is None
            else [e for e in self._buffer if e.timestamp > watermark]
        )
        held.sort(key=lambda e: e.timestamp)
        return tuple(held)

    def last_delivered(self) -> HLCTimestamp | None:
        """마지막으로 배달한 사건의 타임스탬프(아직 없으면 None)."""
        return self._last_delivered

    def buffer_size(self) -> int:
        """버퍼에 적재된(아직 배달 안 된) 사건 수.

        ``deliverable()`` 과 ``pending()`` 이 모두 빈 튜플일 때, 버퍼가 진짜 비었는지
        (size 0) 아니면 워터마크 미형성으로 보류 중인지를 구분하는 데 쓴다.
        """
        return len(self._buffer)


class FederationDeliveryCoordinator:
    """메시(Phase 432) 전파 + HLC 인과-안정 배달(Phase 434)의 결정적 결합.

    메시의 각 인스턴스마다 :class:`CausalDeliveryBuffer` 를 하나씩 두고, origin 의
    사건을 :meth:`FederationMesh.propagate` 로 도달 가능한 모든 인스턴스(origin 제외)
    버퍼에 멱등 주입한다. 각 버퍼는 전체 인스턴스를 예상 출처(자기 제외)로 가지므로,
    연결 메시에서 모든 인스턴스가 서로의 사건을 동일한 안정 순서로 배달한다.

    스냅샷 모델(인접 :class:`FederationMesh` 와 동일): 인스턴스 집합·버퍼는 생성
    시점에 1회 고정한다. 이후 ``mesh.rebuild()`` 로 토폴로지가 바뀌면 새 코디네이터를
    만든다 — 기존 버퍼의 예상 출처 집합은 갱신되지 않는다(신규 인스턴스 사건은
    예상 외 출처로 거부됨).
    """

    def __init__(self, mesh: FederationMesh) -> None:
        self._mesh = mesh
        all_ids = set(mesh.instances())
        self._buffers: dict[str, CausalDeliveryBuffer] = {
            iid: CausalDeliveryBuffer(iid, sources=all_ids) for iid in mesh.instances()
        }

    def broadcast(
        self, event: FederationEvent, ttl: int | None = None
    ) -> tuple[str, ...]:
        """origin(=event.source)의 사건을 도달 가능한 모든 인스턴스 버퍼에 주입한다.

        주입 대상(origin 제외)을 정렬해 반환한다. origin 이 메시에 없으면 ``KeyError``.
        새로 받은 인스턴스만 반환에 포함한다(중복 주입은 멱등 무시되어 제외).
        """
        reach = self._mesh.propagate(event.source, ttl)
        delivered_to: list[str] = []
        for iid in sorted(reach):
            if iid == event.source:
                continue
            if self._buffers[iid].receive(event):
                delivered_to.append(iid)
        return tuple(delivered_to)

    def buffer(self, instance_id: str) -> CausalDeliveryBuffer:
        """해당 인스턴스의 배달 버퍼를 반환한다. 미등록이면 ``KeyError``."""
        return self._buffers[instance_id]

    def flush(self, instance_id: str) -> tuple[FederationEvent, ...]:
        """해당 인스턴스의 안정 사건을 배달한다(버퍼 ``flush`` 위임)."""
        return self._buffers[instance_id].flush()

    def flush_all(self) -> dict[str, tuple[FederationEvent, ...]]:
        """모든 인스턴스를 정렬 순서로 flush 한 결과 맵 {id: 배달 튜플}."""
        return {iid: self._buffers[iid].flush() for iid in sorted(self._buffers)}
