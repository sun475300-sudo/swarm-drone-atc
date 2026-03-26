"""규칙 기반 키워드 매칭 엔진."""

from __future__ import annotations

from pathlib import Path

from chatbot.engine.base import (
    ANSWER_TEMPLATE,
    ESCALATION_KEYWORDS,
    ESCALATION_MESSAGE,
    BaseEngine,
    ChatResponse,
)
from chatbot.knowledge.loader import KnowledgeIndex, KnowledgeLoader

# 한국어 조사 (접미사) 제거 목록 — 긴 것부터 먼저 매칭
_KOREAN_PARTICLES = sorted(
    [
        "에서는", "으로는", "에서", "으로", "부터", "까지",
        "에게", "한테", "처럼", "만큼", "라고", "이라",
        "은", "는", "이", "가", "을", "를", "에", "의",
        "로", "도", "만", "와", "과", "하고", "요",
    ],
    key=len,
    reverse=True,
)

# 매칭 신뢰도 임계값
_CONFIDENCE_THRESHOLD = 0.15


class RuleEngine(BaseEngine):
    """키워드 매칭 기반 규칙 엔진."""

    def __init__(self, knowledge_dir: str | Path | None = None):
        loader = KnowledgeLoader(knowledge_dir)
        self.index: KnowledgeIndex = loader.load()

    def query(self, user_input: str) -> ChatResponse | None:
        """사용자 입력에 대한 최적 응답을 반환한다."""
        if not user_input or not user_input.strip():
            return None

        # 에스컬레이션 체크
        escalation = self._check_escalation(user_input)
        if escalation:
            return escalation

        # 토큰화 및 조사 제거
        tokens = self._tokenize(user_input)
        if not tokens:
            return None

        # 점수 계산
        scores: dict[str, float] = {}
        for token in tokens:
            token_lower = token.lower()
            # 키워드 인덱스에서 정확한 매칭
            if token_lower in self.index.keyword_index:
                for entry_id, weight in self.index.keyword_index[token_lower]:
                    scores[entry_id] = scores.get(entry_id, 0.0) + weight

            # 부분 매칭 (키워드에 토큰이 포함되거나 토큰에 키워드가 포함)
            for kw, entries in self.index.keyword_index.items():
                if kw == token_lower:
                    continue
                if len(token_lower) >= 2 and (
                    token_lower in kw or kw in token_lower
                ):
                    for entry_id, weight in entries:
                        scores[entry_id] = (
                            scores.get(entry_id, 0.0) + weight * 0.5
                        )

        if not scores:
            return None

        # 각 항목의 키워드 수로 정규화
        normalized: dict[str, float] = {}
        for entry_id, score in scores.items():
            entry = self.index.entries.get(entry_id)
            if entry:
                max_possible = sum(
                    w
                    for eid, w in self.index.keyword_index.get(
                        entry.keywords[0].lower(), []
                    )
                    if eid == entry_id
                ) * len(entry.keywords) if entry.keywords else 1.0
                max_possible = max(max_possible, 1.0)
                normalized[entry_id] = score / max_possible

        # 상위 결과
        best_id = max(normalized, key=lambda k: normalized[k])
        best_score = normalized[best_id]

        if best_score < _CONFIDENCE_THRESHOLD:
            return None

        entry = self.index.entries[best_id]
        confidence = min(best_score, 1.0)

        formatted_answer = ANSWER_TEMPLATE.format(
            category=entry.category,
            answer=entry.answer.strip(),
            law_basis="- " + entry.law_basis if entry.law_basis else "- 해당 없음",
        )

        return ChatResponse(
            answer=formatted_answer,
            confidence=confidence,
            category=entry.category,
            entry_id=entry.id,
            law_basis=entry.law_basis,
            related_ids=entry.related,
            source="rule",
        )

    def get_categories(self) -> list[dict]:
        """사용 가능한 카테고리 목록을 반환한다."""
        return [
            {
                "name": cat.name,
                "category_id": cat.category_id,
                "law_references": cat.law_references,
                "entry_count": cat.entry_count,
            }
            for cat in self.index.categories
        ]

    def get_entry_by_id(self, entry_id: str) -> dict | None:
        """ID로 지식베이스 항목을 조회한다."""
        entry = self.index.get_entry(entry_id)
        if entry is None:
            return None
        return {
            "id": entry.id,
            "question": entry.question,
            "answer": entry.answer,
            "law_basis": entry.law_basis,
            "category": entry.category,
            "related": entry.related,
        }

    def get_related_questions(self, entry_id: str) -> list[dict]:
        """관련 질문 목록을 반환한다."""
        entry = self.index.get_entry(entry_id)
        if entry is None:
            return []
        results = []
        for rid in entry.related:
            related_entry = self.index.get_entry(rid)
            if related_entry:
                results.append(
                    {"id": related_entry.id, "question": related_entry.question}
                )
        return results

    def _tokenize(self, text: str) -> list[str]:
        """텍스트를 토큰화하고 한국어 조사를 제거한다."""
        # 특수문자 제거 및 분할
        cleaned = ""
        for ch in text:
            if ch.isalnum() or ch == " " or ord(ch) > 0x1100:
                cleaned += ch
            else:
                cleaned += " "

        raw_tokens = cleaned.split()
        tokens = []
        for token in raw_tokens:
            stripped = self._strip_particles(token)
            if len(stripped) >= 1:
                tokens.append(stripped)
            if stripped != token and len(token) >= 2:
                tokens.append(token)
        return tokens

    def _strip_particles(self, word: str) -> str:
        """한국어 조사를 제거한다."""
        for particle in _KOREAN_PARTICLES:
            if word.endswith(particle) and len(word) > len(particle):
                return word[: -len(particle)]
        return word

    def _check_escalation(self, text: str) -> ChatResponse | None:
        """에스컬레이션이 필요한 키워드가 있는지 확인한다."""
        for keyword in ESCALATION_KEYWORDS:
            if keyword in text:
                return ChatResponse(
                    answer=ESCALATION_MESSAGE,
                    confidence=1.0,
                    category="에스컬레이션",
                    entry_id="escalation",
                    law_basis="",
                    related_ids=[],
                    source="rule",
                    needs_escalation=True,
                    escalation_reason=f"'{keyword}' 관련 문의",
                )
        return None
