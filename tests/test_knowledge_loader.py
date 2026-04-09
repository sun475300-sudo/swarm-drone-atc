"""지식베이스 로더 단위 테스트."""

from pathlib import Path

import pytest

from chatbot.knowledge.loader import KnowledgeLoader, KnowledgeIndex, KnowledgeEntry

_KNOWLEDGE_DIR = Path(__file__).parent.parent / "chatbot" / "knowledge"


class TestKnowledgeLoader:
    """KnowledgeLoader 테스트."""

    def test_loads_all_yaml_files(self):
        index = KnowledgeLoader(_KNOWLEDGE_DIR).load()
        assert isinstance(index, KnowledgeIndex)
        assert len(index.entries) > 0

    def test_has_five_categories(self):
        index = KnowledgeLoader(_KNOWLEDGE_DIR).load()
        assert len(index.categories) == 5

    def test_all_entries_have_required_fields(self):
        index = KnowledgeLoader(_KNOWLEDGE_DIR).load()
        for entry_id, entry in index.entries.items():
            assert isinstance(entry, KnowledgeEntry)
            assert entry.id == entry_id
            assert entry.question
            assert entry.answer
            assert entry.category
            assert entry.category_id
            assert isinstance(entry.keywords, list)
            assert len(entry.keywords) > 0

    def test_keyword_index_built(self):
        index = KnowledgeLoader(_KNOWLEDGE_DIR).load()
        assert len(index.keyword_index) > 0

    def test_keyword_index_has_weights(self):
        index = KnowledgeLoader(_KNOWLEDGE_DIR).load()
        for kw, entries in index.keyword_index.items():
            for entry_id, weight in entries:
                assert isinstance(weight, float)
                assert weight > 0

    def test_get_entry_by_id(self):
        index = KnowledgeLoader(_KNOWLEDGE_DIR).load()
        entry = index.get_entry("general_001")
        assert entry is not None
        assert entry.id == "general_001"
        assert "보세전시장" in entry.question

    def test_get_entry_nonexistent(self):
        index = KnowledgeLoader(_KNOWLEDGE_DIR).load()
        assert index.get_entry("nonexistent_999") is None

    def test_categories_have_entry_counts(self):
        index = KnowledgeLoader(_KNOWLEDGE_DIR).load()
        total = sum(cat.entry_count for cat in index.categories)
        assert total == len(index.entries)

    def test_related_ids_reference_existing_entries(self):
        index = KnowledgeLoader(_KNOWLEDGE_DIR).load()
        for entry in index.entries.values():
            for rid in entry.related:
                assert rid in index.entries, (
                    f"Entry {entry.id} references non-existent related entry {rid}"
                )
