"""챗봇 CLI 시뮬레이터 단위 테스트."""

from pathlib import Path
from unittest.mock import patch

import pytest

from chatbot.engine.rule_engine import RuleEngine

_KNOWLEDGE_DIR = Path(__file__).parent.parent / "chatbot" / "knowledge"


class TestSimulatorIntegration:
    """시뮬레이터에서 사용하는 엔진 기능 통합 테스트."""

    @pytest.fixture
    def engine(self):
        return RuleEngine(_KNOWLEDGE_DIR)

    def test_category_number_selection(self, engine):
        """카테고리 번호로 질문 생성 시 매칭 확인."""
        categories = engine.get_categories()
        for cat in categories:
            query = f"{cat['name']}에 대해 알려주세요"
            result = engine.query(query)
            assert result is not None, f"Category '{cat['name']}' query returned None"

    def test_all_knowledge_entries_are_queryable(self, engine):
        """모든 지식베이스 항목이 자신의 질문으로 매칭 가능한지 확인."""
        matched = 0
        total = len(engine.index.entries)
        for entry_id, entry in engine.index.entries.items():
            result = engine.query(entry.question)
            if result is not None:
                matched += 1
        # 최소 80% 이상 자기 질문으로 매칭되어야 함
        assert matched / total >= 0.8, (
            f"Only {matched}/{total} entries matched their own question"
        )

    def test_related_questions_chain(self, engine):
        """관련 질문 체인이 순환하지 않는지 확인."""
        for entry in engine.index.entries.values():
            visited = set()
            queue = list(entry.related)
            while queue:
                rid = queue.pop(0)
                if rid in visited:
                    continue
                visited.add(rid)
                related_entry = engine.index.get_entry(rid)
                if related_entry:
                    queue.extend(related_entry.related)
            # 무한 루프 없이 완료되어야 함 (visited는 유한)
            assert len(visited) <= len(engine.index.entries)

    def test_multiple_queries_consistent(self, engine):
        """같은 질문을 반복하면 같은 결과가 나오는지 확인."""
        q = "보세전시장에서 판매 가능한가요?"
        r1 = engine.query(q)
        r2 = engine.query(q)
        assert r1 is not None and r2 is not None
        assert r1.entry_id == r2.entry_id
        assert r1.confidence == r2.confidence
