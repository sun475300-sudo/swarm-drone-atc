# Phase 569: Drone Swarm Compiler — DSL to Bytecode
"""
군집 드론 DSL 컴파일러: 미션 DSL 파싱 → AST → 바이트코드 → 인터프리터 실행.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto


class OpCode(Enum):
    NOP = auto()
    MOVE = auto()
    HOVER = auto()
    LAND = auto()
    TAKEOFF = auto()
    SCAN = auto()
    SEND = auto()
    WAIT = auto()
    JUMP = auto()
    JUMP_IF = auto()
    HALT = auto()


@dataclass
class Instruction:
    opcode: OpCode
    operands: list = field(default_factory=list)


@dataclass
class ASTNode:
    node_type: str
    value: str = ""
    children: list = field(default_factory=list)


class Lexer:
    """간이 렉서."""

    KEYWORDS = {"move", "hover", "land", "takeoff", "scan", "send", "wait", "if", "loop", "halt"}

    def tokenize(self, source: str) -> list[tuple[str, str]]:
        tokens = []
        for line in source.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            for p in parts:
                if p in self.KEYWORDS:
                    tokens.append(("KEYWORD", p))
                elif p.replace(".", "").replace("-", "").isdigit():
                    tokens.append(("NUMBER", p))
                else:
                    tokens.append(("IDENT", p))
        return tokens


class Parser:
    """간이 파서 → AST."""

    def parse(self, tokens: list[tuple[str, str]]) -> ASTNode:
        root = ASTNode("program")
        i = 0
        while i < len(tokens):
            ttype, tval = tokens[i]
            if ttype == "KEYWORD":
                if tval == "loop":
                    count = int(tokens[i + 1][1]) if i + 1 < len(tokens) else 1
                    node = ASTNode("loop", str(count))
                    i += 2
                    # Collect body until next keyword at same level
                    body = ASTNode("body")
                    while i < len(tokens) and tokens[i][1] != "end":
                        child = ASTNode("command", tokens[i][1])
                        i += 1
                        while i < len(tokens) and tokens[i][0] != "KEYWORD":
                            child.children.append(ASTNode("arg", tokens[i][1]))
                            i += 1
                        body.children.append(child)
                    node.children.append(body)
                    root.children.append(node)
                else:
                    node = ASTNode("command", tval)
                    i += 1
                    while i < len(tokens) and tokens[i][0] != "KEYWORD":
                        node.children.append(ASTNode("arg", tokens[i][1]))
                        i += 1
                    root.children.append(node)
            else:
                i += 1
        return root


class Compiler:
    """AST → 바이트코드."""

    OPCODE_MAP = {
        "move": OpCode.MOVE, "hover": OpCode.HOVER, "land": OpCode.LAND,
        "takeoff": OpCode.TAKEOFF, "scan": OpCode.SCAN, "send": OpCode.SEND,
        "wait": OpCode.WAIT, "halt": OpCode.HALT,
    }

    def compile(self, ast: ASTNode) -> list[Instruction]:
        code = []
        for child in ast.children:
            if child.node_type == "command":
                opcode = self.OPCODE_MAP.get(child.value, OpCode.NOP)
                operands = [c.value for c in child.children]
                code.append(Instruction(opcode, operands))
            elif child.node_type == "loop":
                count = int(child.value)
                body = self.compile(child.children[0]) if child.children else []
                for _ in range(count):
                    code.extend(body)
        code.append(Instruction(OpCode.HALT))
        return code


class Interpreter:
    """바이트코드 인터프리터."""

    def __init__(self):
        self.pc = 0
        self.executed = 0
        self.output: list[str] = []

    def run(self, code: list[Instruction], max_steps=1000) -> list[str]:
        self.pc = 0
        self.executed = 0
        while self.pc < len(code) and self.executed < max_steps:
            inst = code[self.pc]
            self.executed += 1
            if inst.opcode == OpCode.HALT:
                break
            self.output.append(f"{inst.opcode.name} {' '.join(inst.operands)}")
            self.pc += 1
        return self.output


class DroneSwarmCompiler:
    """DSL → 바이트코드 → 실행 파이프라인."""

    def __init__(self, seed=42):
        self.lexer = Lexer()
        self.parser = Parser()
        self.compiler = Compiler()
        self.interpreter = Interpreter()
        self.rng = np.random.default_rng(seed)
        self.programs_compiled = 0

    def compile_and_run(self, source: str) -> list[str]:
        tokens = self.lexer.tokenize(source)
        ast = self.parser.parse(tokens)
        code = self.compiler.compile(ast)
        self.programs_compiled += 1
        return self.interpreter.run(code)

    def generate_random_program(self, n_commands=10) -> str:
        commands = ["move 10 20 50", "hover", "scan", "wait 5", "send status",
                     "takeoff", "land", "move -5 10 30"]
        lines = []
        for _ in range(n_commands):
            lines.append(commands[int(self.rng.integers(0, len(commands)))])
        lines.append("halt")
        return "\n".join(lines)

    def summary(self):
        return {
            "programs_compiled": self.programs_compiled,
            "instructions_executed": self.interpreter.executed,
            "output_lines": len(self.interpreter.output),
        }


if __name__ == "__main__":
    dsc = DroneSwarmCompiler(42)
    src = dsc.generate_random_program(15)
    output = dsc.compile_and_run(src)
    print(f"Compiled & executed: {len(output)} instructions")
    print(dsc.summary())
