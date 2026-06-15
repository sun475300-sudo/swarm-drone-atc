"""ODYSSEY Phase 425 (Federation): 연합 NOTAM 전파 — 동적 NFZ 브로드캐스트.

한 SDACS 인스턴스(USS)가 발효한 동적 비행금지구역(NFZ)을, 그 구역과 4D로
겹치는 인접 인스턴스에만 **결정적으로** 전파하는 in-process 모델이다. NFZ는
:class:`~simulation.federation_discovery.Volume4D` (로컬 ENU 직육면체 + 시간 창)로
표현하고, 인접 인스턴스 발견은 Phase 421
:class:`~simulation.federation_discovery.FederationDiscoveryService` 의
``query`` (그리드 셀 후보 → 정밀 4D 교차)에 위임한다.

외부 네트워크·랜덤 없이 동작하며 동일한 입력 시퀀스는 항상 동일한 전파 로그를
만든다(재현성). 전파 결정은 세 종류다:

- **DELIVERED** — 이웃이 아직 보유하지 않은 NOTAM(또는 더 높은 버전)을 전달.
- **DUPLICATE** — 이웃이 이미 동일 ``(notam_id, version)`` 을 보유 → 무시(멱등
  재방송/가십에서 발생).
- **REVOKED** — 발효 인스턴스가 철회했거나, NFZ가 이동해 더 이상 겹치지 않는
  이웃의 인박스에서 회수(stale NFZ가 남지 않도록).

각 전달은 불변 :class:`PropagationEvent` 로 기록되어 순서가 보존된 감사 로그가
된다(Phase 429 연합 감사 로그의 기반).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from simulation.federation_discovery import FederationDiscoveryService, Volume4D

# 전파 결정 종류 (정렬·고정).
DELIVERED = "DELIVERED"
DUPLICATE = "DUPLICATE"
REVOKED = "REVOKED"


@dataclass(frozen=True)
class FederatedNotam:
    """전파 대상 NOTAM — 발효 인스턴스·동적 NFZ 볼륨·개정 버전."""

    notam_id: str
    origin: str
    volume: Volume4D
    version: int


@dataclass(frozen=True)
class PropagationEvent:
    """단일 전파 결정의 불변 기록 (감사 로그 1행)."""

    seq: int
    notam_id: str
    origin: str
    target: str
    version: int
    decision: str


@dataclass
class FederationNotamBroadcaster:
    """동적 NFZ를 인접 인스턴스에 전파하는 결정적 브로드캐스터.

    Phase 421 디스커버리 서비스로 겹치는 이웃을 찾고, 각 이웃의 인박스를
    유지한다. NFZ를 재발효(``issue``)하면 버전이 올라가고, 이동해 더는 겹치지
    않게 된 이웃에서는 자동 회수(REVOKED)된다.
    """

    discovery: FederationDiscoveryService
    _inboxes: dict[str, dict[str, FederatedNotam]] = field(default_factory=dict)
    _latest: dict[str, FederatedNotam] = field(default_factory=dict)
    # notam_id → 최초 발효 인스턴스. 철회 후에도 보존해 id 소유권을 영구 고정한다
    # (다른 인스턴스가 같은 id를 탈취하지 못하도록).
    _origin_of: dict[str, str] = field(default_factory=dict)
    _seq: int = 0
    _log: list[PropagationEvent] = field(default_factory=list)

    def _emit(
        self, notam_id: str, origin: str, target: str, version: int, decision: str
    ) -> PropagationEvent:
        self._seq += 1
        event = PropagationEvent(
            seq=self._seq,
            notam_id=notam_id,
            origin=origin,
            target=target,
            version=version,
            decision=decision,
        )
        self._log.append(event)
        return event

    def issue(
        self, origin: str, notam_id: str, volume: Volume4D
    ) -> tuple[PropagationEvent, ...]:
        """동적 NFZ를 발효(또는 갱신)하고 겹치는 이웃에 전파한다.

        같은 ``notam_id`` 재발효는 새 개정으로 처리해 버전을 1 증가시킨다. 갱신
        볼륨과 더는 겹치지 않게 된 기존 보유 이웃에서는 회수(REVOKED)한다.
        ``origin`` 은 디스커버리에 등록된 인스턴스여야 한다.
        """
        if not notam_id:
            raise ValueError("notam_id가 비어 있음")
        if origin not in self.discovery.instances():
            raise ValueError(f"origin 인스턴스 미등록: {origin!r}")

        owner = self._origin_of.get(notam_id)
        if owner is not None and owner != origin:
            raise ValueError(
                f"notam_id {notam_id!r} 의 발효 인스턴스는 {owner!r} 로 고정됨"
            )
        prev = self._latest.get(notam_id)
        version = (prev.version + 1) if prev is not None else 1
        notam = FederatedNotam(notam_id, origin, volume, version)
        self._latest[notam_id] = notam
        self._origin_of[notam_id] = origin

        targets = set(self.discovery.query(volume, exclude=origin))
        events: list[PropagationEvent] = []

        # 갱신 전 보유했으나 새 볼륨과 겹치지 않게 된 이웃에서 회수.
        for target in sorted(self._holders(notam_id) - targets):
            self._withdraw(target, notam_id)
            events.append(self._emit(notam_id, origin, target, version, REVOKED))

        for target in sorted(targets):
            events.append(self._deliver(notam, target))
        return tuple(events)

    def _deliver(self, notam: FederatedNotam, target: str) -> PropagationEvent:
        inbox = self._inboxes.setdefault(target, {})
        held = inbox.get(notam.notam_id)
        # 보유 버전이 같거나 더 높으면 멱등 무시 — stale 패킷이 신버전을 덮어쓰지
        # 못하게 한다(외부 릴레이/가십 유입 대비).
        if held is not None and held.version >= notam.version:
            return self._emit(
                notam.notam_id, notam.origin, target, notam.version, DUPLICATE
            )
        inbox[notam.notam_id] = notam
        return self._emit(
            notam.notam_id, notam.origin, target, notam.version, DELIVERED
        )

    def _withdraw(self, target: str, notam_id: str) -> None:
        """이웃 인박스에서 NOTAM을 제거하고, 비면 인박스 자체도 정리한다."""
        inbox = self._inboxes[target]
        del inbox[notam_id]
        if not inbox:
            del self._inboxes[target]

    def rebroadcast(self, notam_id: str) -> tuple[PropagationEvent, ...]:
        """현재 개정을 다시 전파한다(멱등 재방송/가십).

        이미 같은 버전을 보유한 이웃은 DUPLICATE, 새로 겹치게 된 이웃은
        DELIVERED 가 된다. 미발효 ``notam_id`` 면 ``KeyError``.
        """
        notam = self._latest[notam_id]
        targets = set(self.discovery.query(notam.volume, exclude=notam.origin))
        events: list[PropagationEvent] = []
        for target in sorted(self._holders(notam_id) - targets):
            self._withdraw(target, notam_id)
            events.append(
                self._emit(notam_id, notam.origin, target, notam.version, REVOKED)
            )
        for target in sorted(targets):
            events.append(self._deliver(notam, target))
        return tuple(events)

    def revoke(self, notam_id: str) -> tuple[PropagationEvent, ...]:
        """발효한 NFZ를 철회하고 모든 보유 이웃 인박스에서 회수한다.

        미발효 ``notam_id`` 면 ``KeyError``.
        """
        notam = self._latest.pop(notam_id)
        events: list[PropagationEvent] = []
        for target in sorted(self._holders(notam_id)):
            self._withdraw(target, notam_id)
            events.append(
                self._emit(notam_id, notam.origin, target, notam.version, REVOKED)
            )
        return tuple(events)

    def _holders(self, notam_id: str) -> set[str]:
        return {
            inst for inst, inbox in self._inboxes.items() if notam_id in inbox
        }

    def inbox(self, instance_id: str) -> tuple[FederatedNotam, ...]:
        """인스턴스가 현재 보유한 NOTAM을 notam_id 정렬로 반환한다."""
        inbox = self._inboxes.get(instance_id, {})
        return tuple(sorted(inbox.values(), key=lambda n: n.notam_id))

    def active_volumes(self, instance_id: str) -> tuple[Volume4D, ...]:
        """인스턴스가 회피해야 할 외부 NFZ 볼륨을 notam_id 정렬로 반환한다."""
        return tuple(n.volume for n in self.inbox(instance_id))

    def audit_log(self) -> tuple[PropagationEvent, ...]:
        """모든 전파 결정을 발생 순서대로 반환한다(불변)."""
        return tuple(self._log)

    def summary(self) -> dict[str, int]:
        """결정적 상태 요약 — 활성 NOTAM·보유 이웃 수·전파 이벤트 수."""
        return {
            "active_notams": len(self._latest),
            "holder_instances": len(
                {inst for inst, inbox in self._inboxes.items() if inbox}
            ),
            "events": len(self._log),
        }
