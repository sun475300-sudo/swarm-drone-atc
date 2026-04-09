"""vLLM 기반 LLM 응답 엔진 (향후 확장용 스텁)."""

from __future__ import annotations

from pathlib import Path

from chatbot.engine.base import BaseEngine, ChatResponse
from chatbot.engine.rule_engine import RuleEngine


class LLMEngine(BaseEngine):
    """vLLM 기반 RAG 응답 엔진.

    RuleEngine을 리트리버로 사용하여 관련 지식을 검색한 뒤,
    vLLM의 OpenAI-compatible API를 통해 자연어 응답을 생성한다.

    docker-compose.yml의 vLLM 서비스(Qwen2.5-7B-Instruct)와 연동된다.
    """

    def __init__(
        self,
        knowledge_dir: str | Path | None = None,
        vllm_url: str = "http://localhost:8000",
    ):
        self.rule_engine = RuleEngine(knowledge_dir)
        self.vllm_url = vllm_url

    def query(self, user_input: str) -> ChatResponse | None:
        raise NotImplementedError(
            "LLM 엔진은 vLLM 서비스가 필요합니다. "
            "'python main.py chatbot --engine rule'로 규칙 기반 엔진을 사용하세요."
        )

    def get_categories(self) -> list[dict]:
        return self.rule_engine.get_categories()

    def get_entry_by_id(self, entry_id: str) -> dict | None:
        return self.rule_engine.get_entry_by_id(entry_id)
