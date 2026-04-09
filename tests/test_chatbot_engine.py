"""챗봇 엔진 단위 테스트."""

from pathlib import Path

import pytest

from chatbot.engine.base import ChatResponse, ESCALATION_KEYWORDS
from chatbot.engine.rule_engine import RuleEngine

_KNOWLEDGE_DIR = Path(__file__).parent.parent / "chatbot" / "knowledge"


@pytest.fixture
def engine():
    return RuleEngine(_KNOWLEDGE_DIR)


class TestRuleEngine:
    """RuleEngine 테스트."""

    def test_engine_initializes(self, engine):
        assert engine is not None
        assert len(engine.index.entries) > 0

    def test_exact_keyword_match(self, engine):
        result = engine.query("보세전시장이 무엇인가요?")
        assert result is not None
        assert isinstance(result, ChatResponse)
        assert result.confidence > 0

    def test_permit_query(self, engine):
        result = engine.query("보세전시장 특허 신청 요건")
        assert result is not None
        assert result.category in ("특허/운영", "제도 일반")

    def test_import_export_query(self, engine):
        result = engine.query("반입신고는 어떻게 하나요?")
        assert result is not None
        assert "반입" in result.answer or "신고" in result.answer

    def test_sales_query(self, engine):
        result = engine.query("현장에서 판매 가능한가요?")
        assert result is not None
        assert "판매" in result.answer or "직매" in result.answer

    def test_sample_query(self, engine):
        result = engine.query("견본품 반출이 가능한가요?")
        assert result is not None
        assert "견본품" in result.answer or "반출" in result.answer

    def test_food_tasting_query(self, engine):
        result = engine.query("시식용 식품 세관장확인 생략 가능한가요?")
        assert result is not None
        assert "시식" in result.answer or "식품" in result.answer

    def test_maintenance_query(self, engine):
        result = engine.query("보수작업 범위가 어떻게 되나요?")
        assert result is not None
        assert "보수" in result.answer

    def test_no_match_returns_none(self, engine):
        result = engine.query("오늘 날씨가 어떤가요?")
        assert result is None

    def test_empty_input_returns_none(self, engine):
        assert engine.query("") is None
        assert engine.query("   ") is None

    def test_korean_particle_stripping(self, engine):
        r1 = engine.query("관세를 면제받으려면")
        r2 = engine.query("관세 면제")
        # 둘 다 매칭되어야 함 (같은 엔트리일 수도 있고 아닐 수도 있음)
        if r1 and r2:
            assert r1.entry_id == r2.entry_id

    def test_response_has_law_basis(self, engine):
        result = engine.query("보세전시장이 무엇인가요?")
        assert result is not None
        assert result.law_basis

    def test_response_has_answer_template(self, engine):
        result = engine.query("보세전시장이 무엇인가요?")
        assert result is not None
        assert "문의하신 내용은" in result.answer
        assert "근거:" in result.answer
        assert "안내:" in result.answer

    def test_escalation_detection(self, engine):
        result = engine.query("유권해석을 요청합니다")
        assert result is not None
        assert result.needs_escalation is True
        assert result.category == "에스컬레이션"

    def test_escalation_unipass(self, engine):
        result = engine.query("UNI-PASS 오류가 발생했습니다")
        assert result is not None
        assert result.needs_escalation is True

    def test_get_categories(self, engine):
        cats = engine.get_categories()
        assert len(cats) == 5
        for cat in cats:
            assert "name" in cat
            assert "category_id" in cat

    def test_get_entry_by_id(self, engine):
        entry = engine.get_entry_by_id("general_001")
        assert entry is not None
        assert entry["id"] == "general_001"

    def test_get_entry_by_id_nonexistent(self, engine):
        assert engine.get_entry_by_id("nonexistent") is None

    def test_get_related_questions(self, engine):
        related = engine.get_related_questions("general_001")
        assert isinstance(related, list)
        for item in related:
            assert "id" in item
            assert "question" in item

    def test_category_button_query(self, engine):
        """카테고리 버튼 클릭 시뮬레이션."""
        result = engine.query("제도 일반에 대해 알려주세요")
        assert result is not None

    def test_all_escalation_keywords_trigger(self, engine):
        for kw in ESCALATION_KEYWORDS:
            result = engine.query(f"{kw} 관련 질문입니다")
            assert result is not None
            assert result.needs_escalation is True, f"Keyword '{kw}' did not trigger escalation"
