"""보세전시장 민원상담 챗봇 CLI 시뮬레이터.

Dash 서버 없이 터미널에서 챗봇을 테스트할 수 있는 대화형 시뮬레이터.

사용법:
    python -m chatbot.simulator
    python main.py chatbot-sim
"""

from __future__ import annotations

from pathlib import Path

from chatbot.engine.base import WELCOME_MESSAGE, CLARIFICATION_QUESTIONS
from chatbot.engine.rule_engine import RuleEngine

_KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

# ANSI 색상 코드
_BLUE = "\033[94m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_CYAN = "\033[96m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _print_separator():
    print(f"{_CYAN}{'─' * 70}{_RESET}")


def _print_bot(text: str):
    for line in text.split("\n"):
        print(f"  {_GREEN}{line}{_RESET}")


def _print_confidence(confidence: float):
    if confidence >= 0.6:
        color = _GREEN
        label = "높음"
    elif confidence >= 0.3:
        color = _YELLOW
        label = "보통"
    else:
        color = _RED
        label = "낮음"
    print(f"  {color}[신뢰도: {confidence:.0%} ({label})]{_RESET}")


def _print_related(related: list[dict]):
    if related:
        print(f"\n  {_CYAN}관련 질문:{_RESET}")
        for i, q in enumerate(related, 1):
            print(f"    {_CYAN}{i}. {q['question']}{_RESET}")


def run_simulator(engine_type: str = "rule"):
    """터미널 기반 챗봇 시뮬레이터를 실행한다."""
    engine = RuleEngine(_KNOWLEDGE_DIR)
    categories = engine.get_categories()

    print(f"\n{_BOLD}{'=' * 70}{_RESET}")
    print(f"{_BOLD}  보세전시장 민원상담 챗봇 시뮬레이터{_RESET}")
    print(f"{_BOLD}{'=' * 70}{_RESET}\n")

    _print_bot(WELCOME_MESSAGE)
    _print_separator()

    # 카테고리 안내
    print(f"\n  {_BOLD}카테고리 목록 (번호 입력으로 선택 가능):{_RESET}")
    for i, cat in enumerate(categories, 1):
        print(f"    {_YELLOW}{i}. {cat['name']}{_RESET} ({cat['entry_count']}개 Q&A)")

    print(f"\n  {_BOLD}명령어:{_RESET}")
    print(f"    {_YELLOW}/categories{_RESET} — 카테고리 목록")
    print(f"    {_YELLOW}/questions{_RESET}  — 확인 질문 목록")
    print(f"    {_YELLOW}/help{_RESET}       — 도움말")
    print(f"    {_YELLOW}/quit{_RESET}       — 종료")

    _print_separator()

    while True:
        try:
            user_input = input(f"\n{_BLUE}{_BOLD}민원인 > {_RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n\n{_GREEN}챗봇을 종료합니다. 감사합니다.{_RESET}\n")
            break

        if not user_input:
            continue

        # 명령어 처리
        if user_input.startswith("/"):
            cmd = user_input.lower()
            if cmd in ("/quit", "/exit", "/q"):
                print(f"\n{_GREEN}챗봇을 종료합니다. 감사합니다.{_RESET}\n")
                break
            elif cmd == "/categories":
                print(f"\n  {_BOLD}카테고리 목록:{_RESET}")
                for i, cat in enumerate(categories, 1):
                    print(f"    {_YELLOW}{i}. {cat['name']}{_RESET}")
                continue
            elif cmd == "/questions":
                print(f"\n  {_BOLD}민원 정확도를 높이기 위한 확인 질문:{_RESET}")
                for i, q in enumerate(CLARIFICATION_QUESTIONS, 1):
                    print(f"    {i}. {q}")
                continue
            elif cmd == "/help":
                print(f"\n  {_BOLD}사용법:{_RESET}")
                print("    - 질문을 자유롭게 입력하세요.")
                print("    - 카테고리 번호(1~5)를 입력하면 해당 분야 안내를 받습니다.")
                print("    - /categories: 카테고리 목록")
                print("    - /questions: 확인 질문 목록")
                print("    - /quit: 종료")
                continue
            else:
                print(f"  {_RED}알 수 없는 명령어입니다. /help를 입력하세요.{_RESET}")
                continue

        # 카테고리 번호 입력
        if user_input.isdigit():
            idx = int(user_input) - 1
            if 0 <= idx < len(categories):
                user_input = f"{categories[idx]['name']}에 대해 알려주세요"
                print(f"  {_CYAN}→ \"{user_input}\"{_RESET}")
            else:
                print(f"  {_RED}1~{len(categories)} 사이의 번호를 입력하세요.{_RESET}")
                continue

        _print_separator()
        print(f"\n{_GREEN}{_BOLD}  챗봇 >{_RESET}\n")

        # 엔진 쿼리
        response = engine.query(user_input)

        if response:
            if response.needs_escalation:
                print(f"  {_RED}{_BOLD}[전문 상담 필요]{_RESET}")

            _print_bot(response.answer)
            _print_confidence(response.confidence)

            # 관련 질문
            related = engine.get_related_questions(response.entry_id)
            _print_related(related)
        else:
            _print_bot(
                "죄송합니다. 질문에 맞는 답변을 찾지 못했습니다.\n\n"
                "다음 방법을 시도해 보세요:\n"
                "1. 카테고리 번호(1~5)를 입력해 주세요.\n"
                "2. 다른 키워드로 다시 질문해 주세요.\n"
                "3. 관세청 고객지원센터(125)로 문의해 주세요."
            )

        _print_separator()


if __name__ == "__main__":
    run_simulator()
