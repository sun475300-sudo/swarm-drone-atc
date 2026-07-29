"""
Phase 422: Knowledge Graph Engine for Drone Mission Reasoning
"""

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class Entity:
    """``Entity`` 관련 기능을 제공한다."""
    entity_id: str
    entity_type: str
    properties: dict[str, Any]
    embeddings: np.ndarray


@dataclass
class Relation:
    """``Relation`` 관련 기능을 제공한다."""
    source_id: str
    target_id: str
    relation_type: str
    weight: float = 1.0


class KnowledgeGraphEngine:
    """``KnowledgeGraphEngine`` 역할을 담당한다."""
    def __init__(self, embedding_dim: int = 128):
        """인스턴스를 초기화한다."""
        self.embedding_dim = embedding_dim
        self.entities: dict[str, Entity] = {}
        self.relations: list[Relation] = []
        self.adjacency: dict[str, set[str]] = {}

    def add_entity(self, entity_id: str, entity_type: str, properties: dict[str, Any]):
        """`entity` 항목을 추가한다."""
        embeddings = np.random.randn(self.embedding_dim) * 0.1
        entity = Entity(entity_id, entity_type, properties, embeddings)
        self.entities[entity_id] = entity

        if entity_id not in self.adjacency:
            self.adjacency[entity_id] = set()

    def add_relation(self, source_id: str, target_id: str, relation_type: str):
        """`relation` 항목을 추가한다."""
        if source_id not in self.entities or target_id not in self.entities:
            return

        relation = Relation(source_id, target_id, relation_type)
        self.relations.append(relation)

        self.adjacency[source_id].add(target_id)

    def query(self, entity_id: str, relation_type: str | None = None) -> list[str]:
        """``query`` 동작을 수행한다."""
        if entity_id not in self.adjacency:
            return []

        results = []
        for rel in self.relations:
            if rel.source_id == entity_id and (relation_type is None or rel.relation_type == relation_type):
                results.append(rel.target_id)

        return results

    def find_path(
        self, source: str, target: str, max_depth: int = 3
    ) -> list[str] | None:
        """``find_path`` 동작을 수행한다."""
        queue = [(source, [source])]
        visited = {source}

        while queue:
            current, path = queue.pop(0)

            if current == target:
                return path

            if len(path) >= max_depth:
                continue

            for neighbor in self.adjacency.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None

    def compute_similarity(self, entity1_id: str, entity2_id: str) -> float:
        """`similarity` 값을 계산한다."""
        if entity1_id not in self.entities or entity2_id not in self.entities:
            return 0.0

        e1 = self.entities[entity1_id].embeddings
        e2 = self.entities[entity2_id].embeddings

        return float(np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2) + 1e-6))

    def get_subgraph(self, entity_id: str, depth: int = 2) -> dict[str, Any]:
        """`subgraph` 정보를 조회한다."""
        subgraph_entities = {entity_id}
        queue = [(entity_id, 0)]
        visited = {entity_id}

        while queue:
            current, d = queue.pop(0)
            if d >= depth:
                continue

            for neighbor in self.adjacency.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    subgraph_entities.add(neighbor)
                    queue.append((neighbor, d + 1))

        subgraph_relations = [
            r
            for r in self.relations
            if r.source_id in subgraph_entities and r.target_id in subgraph_entities
        ]

        return {
            "entities": list(subgraph_entities),
            "relations": [
                (r.source_id, r.target_id, r.relation_type) for r in subgraph_relations
            ],
        }
