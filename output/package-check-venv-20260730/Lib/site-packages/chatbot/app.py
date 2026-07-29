"""보세전시장 민원상담 챗봇 Dash 웹 애플리케이션."""

from __future__ import annotations

from pathlib import Path

import dash
from dash import Input, Output, State, ctx, dcc, html

from chatbot.engine.base import WELCOME_MESSAGE, ChatResponse
from chatbot.engine.rule_engine import RuleEngine

_ASSETS_DIR = Path(__file__).parent / "assets"
_KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

# 매칭 실패 시 안내 메시지
_NO_MATCH_MESSAGE = (
    "죄송합니다. 질문에 맞는 답변을 찾지 못했습니다.\n\n"
    "다음 방법을 시도해 보세요:\n"
    "1. 위의 카테고리 버튼을 클릭해 주세요.\n"
    "2. 다른 키워드로 다시 질문해 주세요.\n"
    "3. 관세청 고객지원센터(125)로 문의해 주세요.\n\n"
    "예시 질문:\n"
    "- 보세전시장이 무엇인가요?\n"
    "- 반입신고는 어떻게 하나요?\n"
    "- 현장 판매가 가능한가요?\n"
    "- 견본품 반출 절차가 궁금합니다.\n"
    "- 시식용 식품의 요건확인은?"
)


def create_app(engine_type: str = "rule") -> dash.Dash:
    """챗봇 Dash 애플리케이션을 생성한다."""
    if engine_type == "rule":
        engine = RuleEngine(_KNOWLEDGE_DIR)
    else:
        from chatbot.engine.llm_engine import LLMEngine
        engine = LLMEngine(_KNOWLEDGE_DIR)

    app = dash.Dash(
        __name__,
        assets_folder=str(_ASSETS_DIR),
        title="보세전시장 민원상담 챗봇",
    )

    categories = engine.get_categories()

    app.layout = html.Div(
        className="chatbot-container",
        children=[
            # 헤더
            html.Div(
                className="chatbot-header",
                children=[
                    html.H2("보세전시장 민원상담 챗봇"),
                    html.P(
                        "관세법 및 관세청 공식 자료 기반 보세전시장 민원 안내 서비스"
                    ),
                ],
            ),
            # 카테고리 버튼
            html.Div(
                className="category-buttons",
                children=[
                    html.Button(
                        cat["name"],
                        id={"type": "cat-btn", "index": i},
                        className="category-btn",
                        n_clicks=0,
                    )
                    for i, cat in enumerate(categories)
                ],
            ),
            # 채팅 영역
            html.Div(id="chat-history", className="chat-history"),
            # 입력 영역
            html.Div(
                className="input-area",
                children=[
                    dcc.Input(
                        id="user-input",
                        type="text",
                        placeholder="질문을 입력하세요...",
                        debounce=False,
                        n_submit=0,
                    ),
                    html.Button("전송", id="send-btn", className="send-btn", n_clicks=0),
                ],
            ),
            # 푸터
            html.Div(
                className="chatbot-footer",
                children=[
                    html.P(
                        "본 챗봇은 일반적인 안내용이며, 최종 처리는 관할 세관 확인이 필요합니다."
                    ),
                    html.P(
                        "관세청 고객지원센터: 125 | 전자통관 기술지원: 1544-1285"
                    ),
                ],
            ),
            # 대화 상태 저장소
            dcc.Store(id="conversation-store", data=[]),
            # 관련 질문 클릭용 저장소
            dcc.Store(id="related-click-store", data=""),
        ],
    )

    @app.callback(
        Output("conversation-store", "data"),
        Output("user-input", "value"),
        Input("send-btn", "n_clicks"),
        Input("user-input", "n_submit"),
        Input({"type": "cat-btn", "index": dash.ALL}, "n_clicks"),
        State("user-input", "value"),
        State("conversation-store", "data"),
        prevent_initial_call=True,
    )
    def handle_message(
        send_clicks, n_submit, cat_clicks, user_input, conversation
    ):
        """사용자 메시지를 처리하고 응답을 생성한다."""
        triggered = ctx.triggered_id

        # 카테고리 버튼 클릭
        if isinstance(triggered, dict) and triggered.get("type") == "cat-btn":
            cat_idx = triggered["index"]
            if cat_idx < len(categories):
                user_input = f"{categories[cat_idx]['name']}에 대해 알려주세요"

        if not user_input or not user_input.strip():
            return dash.no_update, dash.no_update

        user_input = user_input.strip()

        # 대화 기록에 사용자 메시지 추가
        conversation = conversation or []
        conversation.append({"role": "user", "content": user_input})

        # 엔진 쿼리
        response: ChatResponse | None = engine.query(user_input)

        if response:
            bot_msg = {
                "role": "bot",
                "content": response.answer,
                "confidence": response.confidence,
                "entry_id": response.entry_id,
                "related_ids": response.related_ids,
                "needs_escalation": response.needs_escalation,
            }
        else:
            bot_msg = {
                "role": "bot",
                "content": _NO_MATCH_MESSAGE,
                "confidence": 0.0,
                "entry_id": "",
                "related_ids": [],
                "needs_escalation": False,
            }

        conversation.append(bot_msg)
        return conversation, ""

    @app.callback(
        Output("chat-history", "children"),
        Input("conversation-store", "data"),
    )
    def render_chat(conversation):
        """대화 기록을 렌더링한다."""
        if not conversation:
            # 초기 환영 메시지
            return [
                _render_bot_message(
                    WELCOME_MESSAGE, confidence=1.0, entry_id="", related_ids=[]
                )
            ]

        children = []
        for msg in conversation:
            if msg["role"] == "user":
                children.append(_render_user_message(msg["content"]))
            else:
                children.append(
                    _render_bot_message(
                        msg["content"],
                        confidence=msg.get("confidence", 0.0),
                        entry_id=msg.get("entry_id", ""),
                        related_ids=msg.get("related_ids", []),
                        needs_escalation=msg.get("needs_escalation", False),
                    )
                )
        return children

    def _render_user_message(content: str) -> html.Div:
        return html.Div(
            className="message-bubble user",
            children=[
                html.Div("나", className="message-label"),
                html.Div(content, className="message-content user"),
            ],
        )

    def _render_bot_message(
        content: str,
        confidence: float = 0.0,
        entry_id: str = "",
        related_ids: list | None = None,
        needs_escalation: bool = False,
    ) -> html.Div:
        children = []

        if needs_escalation:
            children.append(
                html.Span("전문 상담 필요", className="escalation-badge")
            )

        # 신뢰도 배지
        label_children = ["챗봇"]
        if confidence > 0 and entry_id:
            if confidence >= 0.6:
                badge_class = "confidence-badge confidence-high"
            elif confidence >= 0.3:
                badge_class = "confidence-badge confidence-mid"
            else:
                badge_class = "confidence-badge confidence-low"
            label_children.append(
                html.Span(
                    f"신뢰도 {confidence:.0%}",
                    className=badge_class,
                )
            )

        children.append(html.Div(label_children, className="message-label"))
        children.append(html.Div(content, className="message-content bot"))

        # 관련 질문 표시
        if related_ids:
            related_questions = []
            for rid in related_ids:
                entry_data = engine.get_entry_by_id(rid)
                if entry_data:
                    related_questions.append(entry_data["question"])
            if related_questions:
                children.append(
                    html.Div(
                        className="related-questions",
                        children=[
                            html.Span("관련 질문:"),
                            *[
                                html.Span(q, className="related-link")
                                for q in related_questions
                            ],
                        ],
                    )
                )

        return html.Div(className="message-bubble bot", children=children)

    return app


def run_chatbot(port: int = 8051, engine_type: str = "rule", debug: bool = False):
    """챗봇 서버를 실행한다."""
    app = create_app(engine_type=engine_type)
    app.run(debug=debug, host="0.0.0.0", port=port)
