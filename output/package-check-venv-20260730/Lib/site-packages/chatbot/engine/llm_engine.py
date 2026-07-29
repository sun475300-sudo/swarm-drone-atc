"""vLLM-backed response engine with safe rule-engine fallback."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from chatbot.engine.base import SYSTEM_PROMPT, BaseEngine, ChatResponse
from chatbot.engine.rule_engine import RuleEngine


class LLMEngine(BaseEngine):
    """vLLM-backed RAG response engine.

    The rule engine acts as a retriever and as a safe fallback when the local
    vLLM service is unavailable.
    """

    def __init__(
        self,
        knowledge_dir: str | Path | None = None,
        vllm_url: str = "http://localhost:8000",
        model: str = "Qwen/Qwen2.5-7B-Instruct",
        timeout_s: float = 10.0,
    ) -> None:
        """인스턴스를 초기화한다."""
        self.rule_engine = RuleEngine(knowledge_dir)
        self.vllm_url = vllm_url.rstrip("/") + "/"
        self.model = model
        self.timeout_s = timeout_s

    def query(self, user_input: str) -> ChatResponse | None:
        """``query`` 동작을 수행한다."""
        if not user_input or not user_input.strip():
            return None

        retrieved = self.rule_engine.query(user_input)
        if retrieved and retrieved.needs_escalation:
            return retrieved

        messages = self._build_messages(user_input.strip(), retrieved)
        try:
            answer = self._complete(messages)
        except (OSError, TimeoutError, ValueError, KeyError, URLError, json.JSONDecodeError):
            return retrieved

        answer = answer.strip()
        if not answer:
            return retrieved

        if retrieved is None:
            return ChatResponse(
                answer=answer,
                confidence=0.35,
                category="일반 안내",
                entry_id="",
                law_basis="",
                related_ids=[],
                source="llm",
            )

        return ChatResponse(
            answer=answer,
            confidence=max(retrieved.confidence, 0.55),
            category=retrieved.category,
            entry_id=retrieved.entry_id,
            law_basis=retrieved.law_basis,
            related_ids=retrieved.related_ids,
            source="llm",
            needs_escalation=retrieved.needs_escalation,
            escalation_reason=retrieved.escalation_reason,
        )

    def get_categories(self) -> list[dict]:
        """`categories` 정보를 조회한다."""
        return self.rule_engine.get_categories()

    def get_entry_by_id(self, entry_id: str) -> dict | None:
        """`entry by id` 정보를 조회한다."""
        return self.rule_engine.get_entry_by_id(entry_id)

    def _build_messages(
        self,
        user_input: str,
        retrieved: ChatResponse | None,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]

        if retrieved is None:
            messages.append({"role": "user", "content": user_input})
            return messages

        context_blocks = [
            f"질문: {user_input}",
            f"분류: {retrieved.category}",
            f"지식베이스 항목 ID: {retrieved.entry_id}",
            f"규칙 엔진 신뢰도: {retrieved.confidence:.2f}",
            "우선 참고할 공식 자료 요약:",
            retrieved.answer,
        ]
        if retrieved.law_basis:
            context_blocks.append(f"법적 근거: {retrieved.law_basis}")
        if retrieved.related_ids:
            context_blocks.append("관련 항목 ID: " + ", ".join(retrieved.related_ids))
        context_blocks.append(
            "위 자료를 우선 사용해 더 자연스럽고 간결하게 답하되, 근거가 없으면 추정하지 마세요."
        )

        messages.append({"role": "user", "content": "\n\n".join(context_blocks)})
        return messages

    def _complete(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 600,
        }
        request = Request(
            urljoin(self.vllm_url, "v1/chat/completions"),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_s) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"]
