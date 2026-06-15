"""ODYSSEY Phase 429 (Federation): 연합 감사 로그 — 변조 탐지 해시 체인 + 결정적 병합.

연합(다중 SDACS 인스턴스) 운영의 각 단계 — Phase 421 디스커버리·423 핸드오버·
424 충돌 해소·425 NOTAM 전파·428 신뢰·430 분할뇌 — 는 인스턴스마다 자기 결정을
지역 감사 로그로 남긴다. 이 모듈은 그 항목들을 인스턴스 경계를 넘어 **변조 탐지
가능(tamper-evident)** 한 단일 원장(ledger)으로 통합한다.

설계 원칙(인접 federation_* 모듈과 동일):

- **append-only 해시 체인**: 각 항목은 직전 항목의 다이제스트를 재료에 포함한다.
  중간 항목을 바꾸거나 지우면 이후 모든 다이제스트가 깨져 :meth:`verify` 에서
  검출된다 — 단순 평문 로그와 달리 사후 변조를 숨길 수 없다.
- **결정적**: 외부 네트워크·랜덤 0. 동일 항목 시퀀스는 항상 동일한 원장(다이제스트
  포함)을 만든다 — 재현·독립 검증 가능.
- **불변**: :class:`AuditEntry` 는 frozen 이고 :meth:`entries` 는 방어적 튜플을 반환해
  내부 리스트가 호출자에게 노출되지 않는다.
- **CRDT 류 병합**: 두 인스턴스의 원장은 항목 내용(logical_clock·instance_id·
  event_type·detail)을 키로 한 사전식 전순서로 합쳐 다시 체인을 건다. 병합은
  **교환·결합·멱등** 이라 어느 쪽에서 몇 번을 합치든 같은 통합 원장을 얻는다.

각 인스턴스의 지역 로그는 그 자체로 변조 탐지 가능하고, 통합 원장은 결정적으로
재-체인된 전역 뷰다(같은 입력 → 같은 head 다이제스트).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

# 빈 체인의 가상 시작 다이제스트(64 hex zero) — 첫 항목의 prev_digest.
GENESIS_DIGEST = "0" * 64

# 길이 접두 토큰 사이 구분자(가독성용). 다이제스트 충돌 방지는 길이 접두가 담당하며,
# 식별자 위생(hygiene) 차원에서 입력 필드에 이 문자가 없도록도 검증한다.
_FIELD_SEP = "|"


def _digest(prev_digest: str, logical_clock: int, instance_id: str, event_type: str, detail: str) -> str:
    """직전 다이제스트와 항목 내용으로 체인 다이제스트를 결정적으로 계산한다.

    각 필드를 ``len:value`` 형태로 **길이 접두(length-prefixed)** 직렬화한다. 이렇게
    하면 어떤 필드가 구분자나 숫자를 포함하더라도 두 서로 다른 필드 조합이 같은
    재료 문자열을 만들 수 없어(예: ``("a","bc")`` vs ``("ab","c")``), 다이제스트
    충돌·주입이 구조적으로 불가능하다. ``prev_digest`` 도 동일하게 길이 접두되므로
    내부에서 생성되는 hex 값이든 외부 값이든 안전하다.
    """
    parts = (prev_digest, str(logical_clock), instance_id, event_type, detail)
    material = _FIELD_SEP.join(f"{len(p)}:{p}" for p in parts)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuditEntry:
    """연합 감사 원장의 한 행(불변·해시 체인 연결).

    ``logical_clock`` 은 인스턴스가 부여한 논리 시각(예: Lamport/이벤트 카운터)으로
    인스턴스 내에서 단조 증가한다. ``digest`` 는 ``prev_digest`` 와 내용 필드로부터
    파생되며, ``prev_digest`` 는 직전 항목과의 연결 고리다.
    """

    seq: int  # 원장 내 위치(0-기반). 병합 시 재부여된다.
    logical_clock: int
    instance_id: str
    event_type: str
    detail: str
    prev_digest: str
    digest: str

    def content_key(self) -> tuple[int, str, str, str]:
        """병합 정렬·중복 제거에 쓰는 내용 동일성 키(체인 위치와 무관)."""
        return (self.logical_clock, self.instance_id, self.event_type, self.detail)


@dataclass
class FederationAuditLog:
    """변조 탐지 해시 체인으로 연합 감사 항목을 누적하는 결정적 원장."""

    _entries: list[AuditEntry] = field(default_factory=list)
    _last_clock: dict[str, int] = field(default_factory=dict)

    def record(
        self, instance_id: str, event_type: str, detail: str, logical_clock: int
    ) -> AuditEntry:
        """새 감사 항목을 체인 끝에 추가하고 반환한다.

        경계 검증(조기 실패):

        - ``instance_id`` · ``event_type`` 은 비어 있을 수 없다.
        - 어떤 필드도 예약 구분자 ``"|"`` 를 포함할 수 없다(식별자 위생).
        - ``logical_clock`` 은 같은 인스턴스에서 단조 증가해야 한다(이미 본 값 이하면
          순서 역전/재현 위반이므로 ``ValueError``).

        주의: 이 단조 검증은 단일 인스턴스의 지역 로그에만 적용된다. :meth:`merge` 로
        합쳐진 통합 원장은 분기(fork)된 같은 인스턴스 항목을 보존할 수 있어 항목
        순서가 인스턴스별 단조가 아닐 수 있다(병합 의미는 :meth:`merge` 참조).
        """
        if not instance_id:
            raise ValueError("instance_id가 비어 있음")
        if not event_type:
            raise ValueError("event_type이 비어 있음")
        for name, value in (("instance_id", instance_id), ("event_type", event_type), ("detail", detail)):
            if _FIELD_SEP in value:
                raise ValueError(f"{name}에 예약 구분자 '{_FIELD_SEP}' 사용 불가")
        prev_clock = self._last_clock.get(instance_id)
        if prev_clock is not None and logical_clock <= prev_clock:
            raise ValueError(
                f"logical_clock({logical_clock})이 인스턴스 {instance_id}의 "
                f"직전 값({prev_clock}) 이하 — 단조 증가 위반"
            )
        prev_digest = self._entries[-1].digest if self._entries else GENESIS_DIGEST
        entry = AuditEntry(
            seq=len(self._entries),
            logical_clock=logical_clock,
            instance_id=instance_id,
            event_type=event_type,
            detail=detail,
            prev_digest=prev_digest,
            digest=_digest(prev_digest, logical_clock, instance_id, event_type, detail),
        )
        self._entries.append(entry)
        self._last_clock[instance_id] = logical_clock
        return entry

    def entries(self) -> tuple[AuditEntry, ...]:
        """원장의 모든 항목을 추가 순서대로 반환한다(불변 사본)."""
        return tuple(self._entries)

    def head_digest(self) -> str:
        """체인 끝 다이제스트 — 원장 전체 상태의 변조 탐지 지문. 빈 원장은 GENESIS."""
        return self._entries[-1].digest if self._entries else GENESIS_DIGEST

    def verify(self) -> bool:
        """체인 무결성 검증 — 모든 항목의 prev/digest 가 재계산과 일치하는지 확인."""
        prev_digest = GENESIS_DIGEST
        for entry in self._entries:
            if entry.prev_digest != prev_digest:
                return False
            expected = _digest(
                prev_digest,
                entry.logical_clock,
                entry.instance_id,
                entry.event_type,
                entry.detail,
            )
            if entry.digest != expected:
                return False
            prev_digest = entry.digest
        return True

    def query(
        self, instance_id: str | None = None, event_type: str | None = None
    ) -> tuple[AuditEntry, ...]:
        """인스턴스·이벤트 종류로 필터링한 항목을 순서대로 반환한다."""
        return tuple(
            e
            for e in self._entries
            if (instance_id is None or e.instance_id == instance_id)
            and (event_type is None or e.event_type == event_type)
        )

    def merge(self, other: "FederationAuditLog") -> "FederationAuditLog":
        """두 원장을 결정적으로 병합한 새 원장을 반환한다(원본 둘 다 불변).

        내용 키(:meth:`AuditEntry.content_key`)가 같은 항목은 동일 이벤트로 보고 한
        번만 남긴다(멱등). 남은 항목을 그 키의 사전식 전순서로 정렬해 새 체인을
        건다. 따라서 ``a.merge(b)`` 와 ``b.merge(a)`` 는 같은 head 다이제스트를
        만든다(교환). 입력 원장이 둘 다 valid 해도 내용이 모순이면(같은 키, 다른
        체인 결과) 합쳐진 결과는 단일 정렬 체인이라 항상 valid 하다.
        """
        keys: set[tuple[int, str, str, str]] = set()
        for entry in (*self._entries, *other._entries):
            keys.add(entry.content_key())
        merged = FederationAuditLog()
        prev_digest = GENESIS_DIGEST
        for seq, key in enumerate(sorted(keys)):
            clock, instance_id, event_type, detail = key
            entry = AuditEntry(
                seq=seq,
                logical_clock=clock,
                instance_id=instance_id,
                event_type=event_type,
                detail=detail,
                prev_digest=prev_digest,
                digest=_digest(prev_digest, clock, instance_id, event_type, detail),
            )
            merged._entries.append(entry)
            merged._last_clock[instance_id] = max(merged._last_clock.get(instance_id, clock), clock)
            prev_digest = entry.digest
        return merged
