"""
Phase 422: Knowledge Graph Engine for Drone Mission Reasoning
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
import time
import hashlib


@dataclass
class Entity:
    entity_id: str
    entity_type: str
    properties: Dict[str, Any]
    embeddings: np.ndarray


@dataclass
class Relation:
    source_id: str
    target_id: str
    relation_type: str
    weight: float = 1.0


class KnowledgeGraphEngine:
    def __init__(self, embedding_dim: int = 128):
        self.embedding_dim = embedding_dim
        self.entities: Dict[str, Entity] = {}
        self.relations: List[Relation] = []
        self.adjacency: Dict[str, Set[str]] = {}

    def add_entity(self, entity_id: str, entity_type: str, properties: Dict[str, Any]):
        embeddings = np.random.randn(self.embedding_dim) * 0.1
        entity = Entity(entity_id, entity_type, properties, embeddings)
        self.entities[entity_id] = entity

        if entity_id not in self.adjacency:
            self.adjacency[entity_id] = set()

    def add_relation(self, source_id: str, target_id: str, relation_type: str):
        if source_id not in self.entities or target_id not in self.entities:
            return

        relation = Relation(source_id, target_id, relation_type)
        self.relations.append(relation)

        self.adjacency[source_id].add(target_id)

    def query(self, entity_id: str, relation_type: Optional[str] = None) -> List[str]:
        if entity_id not in self.adjacency:
            return []

        results = []
        for rel in self.relations:
            if rel.source_id == entity_id:
                if relation_type is None or rel.relation_type == relation_type:
                    results.append(rel.target_id)

        return results

    def find_path(
        self, source: str, target: str, max_depth: int = 3
    ) -> Optional[List[str]]:
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
        if entity1_id not in self.entities or entity2_id not in self.entities:
            return 0.0

        e1 = self.entities[entity1_id].embeddings
        e2 = self.entities[entity2_id].embeddings

        return float(np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2) + 1e-6))

    def get_subgraph(self, entity_id: str, depth: int = 2) -> Dict[str, Any]:
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
