# Phase 584: Swarm Language Model — Inter-Drone NLP Protocol
"""
군집 언어 모델: 드론 간 자연어 프로토콜,
토큰화, 임베딩, 시퀀스 생성.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class Token:
    token_id: int
    text: str
    embedding: np.ndarray


class DroneVocabulary:
    """드론 통신 어휘."""

    COMMANDS = [
        "MOVE", "HOVER", "LAND", "TAKEOFF", "SCAN", "REPORT",
        "AVOID", "FOLLOW", "HOLD", "RETURN", "CHARGE", "RELAY",
        "NORTH", "SOUTH", "EAST", "WEST", "UP", "DOWN",
        "URGENT", "NORMAL", "LOW", "HIGH", "CLEAR", "BLOCKED",
        "CONFLICT", "RESOLVED", "PENDING", "ACK", "NACK", "PING",
        "ALTITUDE", "SPEED", "HEADING", "BATTERY", "WIND", "STATUS"
    ]

    def __init__(self, embed_dim=16, seed=42):
        self.rng = np.random.default_rng(seed)
        self.embed_dim = embed_dim
        self.tokens: dict[str, Token] = {}
        for i, cmd in enumerate(self.COMMANDS):
            emb = self.rng.normal(0, 0.5, embed_dim)
            emb /= np.linalg.norm(emb) + 1e-8
            self.tokens[cmd] = Token(i, cmd, emb)

    def encode(self, text: str) -> list[Token]:
        return [self.tokens[w] for w in text.upper().split() if w in self.tokens]

    def similarity(self, a: str, b: str) -> float:
        if a not in self.tokens or b not in self.tokens:
            return 0.0
        return float(self.tokens[a].embedding @ self.tokens[b].embedding)


class SequenceGenerator:
    """시퀀스 생성기 (간이 bigram)."""

    def __init__(self, vocab: DroneVocabulary, seed=42):
        self.rng = np.random.default_rng(seed)
        self.vocab = vocab
        n = len(vocab.COMMANDS)
        self.transition = self.rng.dirichlet(np.ones(n), n)

    def generate(self, start: str, length=5) -> list[str]:
        cmds = self.vocab.COMMANDS
        if start.upper() not in cmds:
            start = cmds[0]
        idx = cmds.index(start.upper())
        seq = [cmds[idx]]
        for _ in range(length - 1):
            idx = int(self.rng.choice(len(cmds), p=self.transition[idx]))
            seq.append(cmds[idx])
        return seq


class SwarmLanguageModel:
    """군집 언어 모델 시뮬레이션."""

    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)
        self.vocab = DroneVocabulary(16, seed)
        self.generator = SequenceGenerator(self.vocab, seed)
        self.messages: list[list[str]] = []
        self.encoded_count = 0

    def communicate(self, n_messages=20, msg_len=5):
        starts = self.rng.choice(self.vocab.COMMANDS, n_messages)
        for s in starts:
            msg = self.generator.generate(s, msg_len)
            self.messages.append(msg)
            self.encoded_count += len(msg)

    def run(self, n_messages=20):
        self.communicate(n_messages)

    def summary(self):
        return {
            "vocabulary_size": len(self.vocab.tokens),
            "embed_dim": self.vocab.embed_dim,
            "messages_sent": len(self.messages),
            "total_tokens": self.encoded_count,
            "unique_commands_used": len(set(t for m in self.messages for t in m)),
        }


if __name__ == "__main__":
    slm = SwarmLanguageModel(42)
    slm.run(20)
    for k, v in slm.summary().items():
        print(f"  {k}: {v}")
