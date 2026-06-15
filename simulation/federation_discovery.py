"""ODYSSEY Phase 421 (Federation): 인스턴스 간 디스커버리 프로토콜 (DSS 유사 결정적 모델).

ASTM F3548-21의 DSS(Discovery and Synchronization Service)를 단순화한 결정적
in-process 모델이다. 여러 SDACS 인스턴스(USS)가 각자 관리하는 4D 공역 볼륨
(x·y·z 직육면체 + 시간 창)을 등록하면, 공간 그리드 셀 인덱스 + 정밀 4D 교차
판정으로 인접 인스턴스를 **결정적으로** 발견하고 동기화 대상을 계산한다.

외부 네트워크·랜덤 없이 동작하며 출력은 항상 정렬된다(재현성). DSS의 핵심 두 가지
역할 — *디스커버리*(겹치는 인스턴스 찾기)와 *동기화*(이웃 목록 유지) — 만 모델링하고
실제 RPC·인증은 범위 밖이다 (production 등급의 결정적 구현).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# 공간 그리드 셀 한 변 길이 (m). 후보 인덱싱 단위 — 정밀 교차는 별도로 확인한다.
DEFAULT_CELL_SIZE_M = 500.0


@dataclass(frozen=True)
class Volume4D:
    """축 정렬 4D 공역 볼륨 — 로컬 ENU 좌표(m) 직육면체 + 시간 창(s).

    경계값 검증은 생성 시점(시스템 경계)에 수행하며, 퇴화 볼륨은 ``ValueError``.
    """

    x_min: float
    x_max: float
    y_min: float
    y_max: float
    z_min: float
    z_max: float
    t_start: float
    t_end: float

    def __post_init__(self) -> None:
        if not (self.x_max > self.x_min):
            raise ValueError("x_max는 x_min보다 커야 함")
        if not (self.y_max > self.y_min):
            raise ValueError("y_max는 y_min보다 커야 함")
        if not (self.z_max > self.z_min):
            raise ValueError("z_max는 z_min보다 커야 함")
        if not (self.t_end > self.t_start):
            raise ValueError("t_end는 t_start보다 커야 함")

    def overlaps(self, other: "Volume4D") -> bool:
        """다른 볼륨과 4개 축(x·y·z·t) 모두에서 교차하면 True (경계 접촉은 비교차)."""
        return (
            self.x_min < other.x_max
            and other.x_min < self.x_max
            and self.y_min < other.y_max
            and other.y_min < self.y_max
            and self.z_min < other.z_max
            and other.z_min < self.z_max
            and self.t_start < other.t_end
            and other.t_start < self.t_end
        )

    def contains(self, x: float, y: float, z: float, t: float) -> bool:
        """4D 점 (x, y, z, t)이 볼륨 내부에 있으면 True (반열린 구간 [min, max)).

        상한 경계는 제외한다(overlaps의 엄격 부등식과 일관). 인접 볼륨이 경계를
        공유할 때 한 점이 양쪽에 동시 귀속되지 않도록 보장한다(핸드오버 결정성).
        """
        return (
            self.x_min <= x < self.x_max
            and self.y_min <= y < self.y_max
            and self.z_min <= z < self.z_max
            and self.t_start <= t < self.t_end
        )


@dataclass(frozen=True)
class Subscription:
    """등록 결과 — 부여된 버전·점유 셀·등록 시점 발견된 이웃 인스턴스."""

    instance_id: str
    version: int
    covered_cells: tuple[tuple[int, int], ...]
    neighbors: tuple[str, ...]


@dataclass
class _Entity:
    instance_id: str
    volume: Volume4D
    version: int
    cells: frozenset[tuple[int, int]]


@dataclass
class FederationDiscoveryService:
    """DSS 유사 결정적 디스커버리·동기화 서비스.

    공간 그리드 셀(``cell_size_m``)로 후보를 좁힌 뒤 정밀 4D 교차로 확정한다.
    동일 ``instance_id`` 재등록은 갱신(볼륨 교체 + 버전 증가)으로 처리한다.
    """

    cell_size_m: float = DEFAULT_CELL_SIZE_M
    _entities: dict[str, _Entity] = field(default_factory=dict)
    _cell_index: dict[tuple[int, int], set[str]] = field(default_factory=dict)
    _version: int = 0

    def __post_init__(self) -> None:
        if self.cell_size_m <= 0:
            raise ValueError("cell_size_m은 0보다 커야 함")

    def _cells_of(self, volume: Volume4D) -> frozenset[tuple[int, int]]:
        """볼륨의 x·y 평면 투영이 닿는 모든 그리드 셀 (ix, iy) 집합."""
        # math.floor 사용: 음수 ENU 좌표에서도 셀 인덱스가 일관되게 내림되도록
        # (int()는 0 방향 절삭이라 음수에서 // 와 어긋남).
        size = self.cell_size_m
        ix0 = math.floor(volume.x_min / size)
        ix1 = math.floor(volume.x_max / size)
        iy0 = math.floor(volume.y_min / size)
        iy1 = math.floor(volume.y_max / size)
        return frozenset(
            (ix, iy)
            for ix in range(ix0, ix1 + 1)
            for iy in range(iy0, iy1 + 1)
        )

    def register(self, instance_id: str, volume: Volume4D) -> Subscription:
        """인스턴스의 관리 볼륨을 등록(또는 갱신)하고 발견된 이웃을 반환한다."""
        if not instance_id:
            raise ValueError("instance_id가 비어 있음")
        if instance_id in self._entities:
            self._unindex(self._entities[instance_id])

        self._version += 1
        cells = self._cells_of(volume)
        entity = _Entity(instance_id, volume, self._version, cells)
        self._entities[instance_id] = entity
        for cell in cells:
            self._cell_index.setdefault(cell, set()).add(instance_id)

        neighbors = self.query(volume, exclude=instance_id)
        return Subscription(
            instance_id=instance_id,
            version=entity.version,
            covered_cells=tuple(sorted(cells)),
            neighbors=neighbors,
        )

    def _unindex(self, entity: _Entity) -> None:
        for cell in entity.cells:
            bucket = self._cell_index.get(cell)
            if bucket is not None:
                bucket.discard(entity.instance_id)
                if not bucket:
                    del self._cell_index[cell]

    def remove(self, instance_id: str) -> None:
        """등록된 인스턴스를 제거한다. 미등록 인스턴스면 ``KeyError``."""
        entity = self._entities.pop(instance_id)
        self._unindex(entity)

    def query(
        self, volume: Volume4D, exclude: str | None = None
    ) -> tuple[str, ...]:
        """질의 볼륨과 4D 교차하는 인스턴스 id를 정렬해 반환한다."""
        candidates: set[str] = set()
        for cell in self._cells_of(volume):
            candidates |= self._cell_index.get(cell, set())
        matched = [
            iid
            for iid in candidates
            if iid != exclude and self._entities[iid].volume.overlaps(volume)
        ]
        return tuple(sorted(matched))

    def covering(self, x: float, y: float, z: float, t: float) -> tuple[str, ...]:
        """4D 점을 포함하는 인스턴스 id를 정렬해 반환한다 (관제권 결정의 1차 입력).

        점이 닿는 그리드 셀의 후보만 정밀 ``Volume4D.contains`` 로 확정한다.
        경계 공유 볼륨은 반열린 구간 규약으로 중복 귀속이 없다.
        """
        ix = math.floor(x / self.cell_size_m)
        iy = math.floor(y / self.cell_size_m)
        # query()와 동일하게 내부 셋의 스냅샷을 떠서 순회한다(반복 중 변경 방지).
        candidates = set(self._cell_index.get((ix, iy), ()))
        matched = [
            iid
            for iid in candidates
            if self._entities[iid].volume.contains(x, y, z, t)
        ]
        return tuple(sorted(matched))

    def synchronization_targets(self, instance_id: str) -> tuple[str, ...]:
        """등록된 인스턴스의 현재 동기화 대상(겹치는 이웃)을 정렬해 반환한다.

        미등록 인스턴스면 ``KeyError``.
        """
        entity = self._entities[instance_id]
        return self.query(entity.volume, exclude=instance_id)

    def instances(self) -> tuple[str, ...]:
        """현재 등록된 모든 인스턴스 id를 정렬해 반환한다."""
        return tuple(sorted(self._entities))

    def summary(self) -> dict[str, int]:
        """결정적 상태 요약 — 인스턴스 수·점유 셀 수·현재 버전."""
        return {
            "instances": len(self._entities),
            "occupied_cells": len(self._cell_index),
            "version": self._version,
        }
