"""지식베이스 YAML 로더 및 인덱스 빌더."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class KnowledgeEntry:
    """지식베이스 개별 항목."""

    id: str
    question: str
    keywords: list[str]
    answer: str
    law_basis: str
    category: str
    category_id: str
    related: list[str] = field(default_factory=list)


@dataclass
class CategoryInfo:
    """카테고리 정보."""

    name: str
    category_id: str
    law_references: list[str]
    entry_count: int


@dataclass
class KnowledgeIndex:
    """로드된 지식베이스 인덱스."""

    entries: dict[str, KnowledgeEntry]
    keyword_index: dict[str, list[tuple[str, float]]]
    categories: list[CategoryInfo]

    def get_entry(self, entry_id: str) -> KnowledgeEntry | None:
        return self.entries.get(entry_id)


class KnowledgeLoader:
    """YAML 파일에서 지식베이스를 로드하고 인덱스를 구축한다."""

    def __init__(self, knowledge_dir: str | Path | None = None):
        if knowledge_dir is None:
            knowledge_dir = Path(__file__).parent
        self.knowledge_dir = Path(knowledge_dir)

    def load(self) -> KnowledgeIndex:
        """모든 YAML 파일을 로드하고 인덱스를 구축한다."""
        entries: dict[str, KnowledgeEntry] = {}
        categories: list[CategoryInfo] = []

        yaml_files = sorted(self.knowledge_dir.glob("*.yaml"))

        for yaml_path in yaml_files:
            cat_data = self._load_yaml(yaml_path)
            if cat_data is None:
                continue

            category_name = cat_data.get("category", "")
            category_id = cat_data.get("category_id", "")
            law_refs = cat_data.get("law_references", [])
            cat_entries = cat_data.get("entries", [])

            for entry_data in cat_entries:
                entry = KnowledgeEntry(
                    id=entry_data["id"],
                    question=entry_data["question"],
                    keywords=entry_data.get("keywords", []),
                    answer=entry_data["answer"],
                    law_basis=entry_data.get("law_basis", ""),
                    category=category_name,
                    category_id=category_id,
                    related=entry_data.get("related", []),
                )
                entries[entry.id] = entry

            categories.append(
                CategoryInfo(
                    name=category_name,
                    category_id=category_id,
                    law_references=law_refs,
                    entry_count=len(cat_entries),
                )
            )

        keyword_index = self._build_keyword_index(entries)
        return KnowledgeIndex(
            entries=entries,
            keyword_index=keyword_index,
            categories=categories,
        )

    def _load_yaml(self, path: Path) -> dict | None:
        """YAML 파일을 로드한다."""
        try:
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f)
        except (yaml.YAMLError, OSError):
            return None

    def _build_keyword_index(
        self, entries: dict[str, KnowledgeEntry]
    ) -> dict[str, list[tuple[str, float]]]:
        """역방향 키워드 인덱스를 구축한다 (IDF 가중치 포함)."""
        # 각 키워드가 몇 개의 항목에 등장하는지 카운트
        doc_freq: dict[str, int] = {}
        for entry in entries.values():
            seen = set()
            for kw in entry.keywords:
                kw_lower = kw.lower()
                if kw_lower not in seen:
                    doc_freq[kw_lower] = doc_freq.get(kw_lower, 0) + 1
                    seen.add(kw_lower)

        total_docs = max(len(entries), 1)

        # IDF 가중치를 적용한 역방향 인덱스
        keyword_index: dict[str, list[tuple[str, float]]] = {}
        for entry in entries.values():
            for kw in entry.keywords:
                kw_lower = kw.lower()
                idf = math.log(total_docs / doc_freq.get(kw_lower, 1)) + 1.0
                if kw_lower not in keyword_index:
                    keyword_index[kw_lower] = []
                keyword_index[kw_lower].append((entry.id, idf))

        return keyword_index
