"""ODYSSEY Phase 431 (Federation): 하이브리드 논리 시계(Hybrid Logical Clock).

3+ 인스턴스 메시 연합에서는 인스턴스마다 벽시계(wall clock)가 어긋나므로, 물리
시각만으로는 인과 순서(causality)를 보장할 수 없다. 순수 Lamport 논리 시계는
인과 순서는 보장하지만 물리 시각과 동떨어져 사람이 읽기 어렵다. **하이브리드 논리
시계(HLC, Kulkarni et al. 2014)** 는 둘을 결합한다:

- 타임스탬프 ``(wall_time, counter)`` 의 ``wall_time`` 은 관측된 물리 시각에 가깝게
  유지되고(읽기 좋음), ``counter`` 는 같은 ``wall_time`` 안의 이벤트를 논리적으로
  구분한다.
- **인과 단조성**: 이벤트 e1 이 e2 보다 happened-before 면 항상
  ``hlc(e1) < hlc(e2)`` (사전식). 따라서 연합 감사 로그(Phase 429)·핸드오버
  (Phase 423) 결정의 전역 순서를 물리 시계 동기화 없이 결정적으로 매길 수 있다.

설계 원칙(인접 federation_* 모듈과 동일):

- **결정적**: 외부 네트워크·랜덤 0. 같은 (local/receive) 이벤트 순서는 항상 같은
  타임스탬프 열을 만든다 — 재현·독립 검증 가능. ``wall_time`` 은 호출자가 넘기는
  정수 물리 시각(예: epoch 밀리초)이며 시스템 시계를 직접 읽지 않는다.
- **불변 타임스탬프**: :class:`HLCTimestamp` 는 frozen 이고 ``(wall_time, counter,
  instance_id)`` 사전식 전순서를 제공한다(``order=True``). 시계 객체 자체는 마지막
  상태를 누적하는 상태형(인접 ``FederationAuditLog`` 과 동일 컨벤션).
- **물리 시계 역행 견딤**: 벽시계가 거꾸로 가도(``wall_time`` 감소) 논리 고점
  ``_wall`` 은 줄지 않고 ``counter`` 만 올라 단조성을 깨지 않는다.

표준 HLC 알고리즘을 그대로 구현한다(검증된 접근 재사용). 멀티 도메인 시각 동기화의
사실상 표준으로 CockroachDB·MongoDB 등이 채택한 방식이다.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class HLCTimestamp:
    """하이브리드 논리 시계의 한 타임스탬프(불변·전순서).

    ``order=True`` 라 ``(wall_time, counter, instance_id)`` 사전식으로 비교된다 —
    인스턴스 간 동률을 ``instance_id`` 로 깨는 **결정적 전순서**. 인과 비교
    (happened-before)는 :pyattr:`causal_key` 로 ``(wall_time, counter)`` 만 본다.
    """

    wall_time: int
    counter: int
    instance_id: str

    def __post_init__(self) -> None:
        if self.wall_time < 0:
            raise ValueError(f"wall_time({self.wall_time})은 음수일 수 없음")
        if self.counter < 0:
            raise ValueError(f"counter({self.counter})는 음수일 수 없음")
        if not self.instance_id:
            raise ValueError("instance_id가 비어 있음")

    @property
    def causal_key(self) -> tuple[int, int]:
        """인과(happened-before) 비교용 키 — 인스턴스 식별자를 뺀 ``(wall, counter)``."""
        return (self.wall_time, self.counter)

    def happened_before(self, other: HLCTimestamp) -> bool:
        """이 타임스탬프가 ``other`` 보다 인과적으로 앞서면 True(인스턴스 무관).

        주의: 이는 **부분 순서** 다. ``causal_key`` 가 같은(동률) 두 타임스탬프는 서로
        다른 인스턴스에서 나온 **동시(concurrent)** 이벤트이며, 양방향 모두 False 를
        반환한다 — ``not a.happened_before(b)`` 가 "b 가 a 보다 앞선다"를 의미하지
        않는다(:meth:`is_concurrent_with` 로 동시성 여부를 명시적으로 확인할 것).
        ``__lt__``(order=True)는 ``instance_id`` 까지 포함한 **전순서** 라 동시 이벤트도
        결정적으로 정렬하지만, 그 순서는 인과 관계를 뜻하지 않는다.
        """
        return self.causal_key < other.causal_key

    def is_concurrent_with(self, other: HLCTimestamp) -> bool:
        """두 타임스탬프가 동시(어느 쪽도 happened-before 아님)면 True.

        HLC 에서 동시성은 ``causal_key`` 동률로 나타난다(같은 인스턴스는 단조 증가라
        동률이 불가능하므로, 동률이면 항상 서로 다른 인스턴스의 동시 이벤트다).
        """
        return self.causal_key == other.causal_key


@dataclass
class HybridLogicalClock:
    """한 연합 인스턴스의 하이브리드 논리 시계(상태형·결정적).

    내부 상태 ``(_wall, _counter)`` 는 마지막으로 발행한 타임스탬프의 논리 고점이다.
    :meth:`local_event` 는 지역 이벤트마다, :meth:`receive_event` 는 다른 인스턴스의
    타임스탬프를 동반한 메시지 수신마다 호출해 새 타임스탬프를 발행한다. 발행되는
    타임스탬프는 항상 직전 발행본보다 **사전식으로 엄격히 증가**한다.
    """

    instance_id: str
    # 초기 고점은 -1(아직 아무것도 발행하지 않은 sentinel). 모든 유효 물리 시각·원격
    # wall(>=0)보다 작으므로, 갓 만든 시계의 첫 이벤트는 (물리 시각, counter=0)으로
    # 발행된다 — 첫 타임스탬프 counter 가 항상 0이 되어 cold-start 모호성이 없다.
    _wall: int = -1
    _counter: int = 0

    def __post_init__(self) -> None:
        if not self.instance_id:
            raise ValueError("instance_id가 비어 있음")

    def _emit(self, wall: int, counter: int) -> HLCTimestamp:
        self._wall = wall
        self._counter = counter
        return HLCTimestamp(wall, counter, self.instance_id)

    def local_event(self, physical_time: int) -> HLCTimestamp:
        """지역 이벤트 발생 시 새 타임스탬프를 발행한다.

        물리 시각이 논리 고점보다 앞서면 ``wall`` 을 그 값으로 올리고 ``counter`` 를
        0으로 리셋한다. 그렇지 않으면(물리 시각이 같거나 역행) ``wall`` 을 유지하고
        ``counter`` 만 1 증가시켜 단조성을 지킨다.
        """
        if physical_time < 0:
            raise ValueError(f"physical_time({physical_time})은 음수일 수 없음")
        wall_old, counter_old = self._wall, self._counter
        wall_new = max(wall_old, physical_time)
        counter_new = 0 if wall_new > wall_old else counter_old + 1
        return self._emit(wall_new, counter_new)

    def receive_event(self, physical_time: int, remote: HLCTimestamp) -> HLCTimestamp:
        """다른 인스턴스의 타임스탬프를 수반한 메시지 수신 시 새 타임스탬프를 발행한다.

        표준 HLC 병합 규칙: 새 ``wall`` 은 (지역 고점·원격 ``wall``·물리 시각)의
        최댓값. ``counter`` 는 그 최댓값이 어디서 왔는지에 따라 결정된다 — 지역·원격이
        함께 최대면 두 카운터의 최댓값 +1, 한쪽만 최대면 그쪽 카운터 +1, 물리 시각이
        새로 최대면 0. 이로써 인과 관계가 타임스탬프 순서에 보존된다.
        """
        if physical_time < 0:
            raise ValueError(f"physical_time({physical_time})은 음수일 수 없음")
        if not isinstance(remote, HLCTimestamp):
            raise TypeError("remote는 HLCTimestamp여야 함")
        wall_old, counter_old = self._wall, self._counter
        wall_remote, counter_remote = remote.wall_time, remote.counter
        wall_new = max(wall_old, wall_remote, physical_time)
        if wall_new == wall_old and wall_new == wall_remote:
            counter_new = max(counter_old, counter_remote) + 1
        elif wall_new == wall_old:
            counter_new = counter_old + 1
        elif wall_new == wall_remote:
            counter_new = counter_remote + 1
        else:
            counter_new = 0
        return self._emit(wall_new, counter_new)

    def current(self) -> HLCTimestamp:
        """마지막으로 발행한(= 현재 논리 고점) 타임스탬프를 반환한다(상태 불변).

        아직 아무 이벤트도 발행하지 않은 갓 만든 시계는 중립 기준점 ``(0, 0)`` 을
        반환한다(내부 sentinel ``-1`` 은 노출하지 않는다).
        """
        return HLCTimestamp(max(self._wall, 0), self._counter, self.instance_id)
