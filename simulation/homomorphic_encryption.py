# Phase 566: Homomorphic Encryption — BGV-like Scheme
"""
동형 암호화: BGV 스킴 근사 시뮬레이션.
암호문 상태에서 덧셈/곱셈 연산, 노이즈 관리.
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class HEParams:
    """``HEParams`` 관련 기능을 제공한다."""
    n: int = 64          # 다항식 차수
    q: int = 65537       # 모듈러스
    t: int = 257         # 평문 모듈러스
    noise_bound: int = 8


@dataclass
class Ciphertext:
    """``Ciphertext`` 관련 기능을 제공한다."""
    c0: np.ndarray
    c1: np.ndarray
    noise_level: float


@dataclass
class SecretKey:
    """``SecretKey`` 관련 기능을 제공한다."""
    s: np.ndarray


@dataclass
class PublicKey:
    """``PublicKey`` 관련 기능을 제공한다."""
    pk0: np.ndarray
    pk1: np.ndarray


class BGVScheme:
    """BGV 동형 암호 (간이)."""

    def __init__(self, params: HEParams = None, seed=42):
        """인스턴스를 초기화한다."""
        self.params = params or HEParams()
        self.rng = np.random.default_rng(seed)
        self.sk, self.pk = self._keygen()

    def _mod(self, x: np.ndarray) -> np.ndarray:
        return x % self.params.q

    def _keygen(self):
        n = self.params.n
        s = self.rng.integers(-1, 2, n)
        a = self.rng.integers(0, self.params.q, n)
        e = self.rng.integers(-self.params.noise_bound, self.params.noise_bound + 1, n)
        pk0 = self._mod(-a * s + e)
        pk1 = a
        return SecretKey(s), PublicKey(pk0, pk1)

    def encrypt(self, plaintext: int) -> Ciphertext:
        """``encrypt`` 동작을 수행한다."""
        n = self.params.n
        m = np.zeros(n, dtype=np.int64)
        m[0] = plaintext % self.params.t
        delta = self.params.q // self.params.t
        scaled = self._mod(m * delta)
        r = self.rng.integers(0, 2, n)
        e0 = self.rng.integers(-self.params.noise_bound, self.params.noise_bound + 1, n)
        e1 = self.rng.integers(-self.params.noise_bound, self.params.noise_bound + 1, n)
        c0 = self._mod(self.pk.pk0 * r + e0 + scaled)
        c1 = self._mod(self.pk.pk1 * r + e1)
        return Ciphertext(c0, c1, float(np.max(np.abs(e0))))

    def decrypt(self, ct: Ciphertext) -> int:
        """``decrypt`` 동작을 수행한다."""
        delta = self.params.q // self.params.t
        raw = self._mod(ct.c0 + ct.c1 * self.sk.s)
        # 반올림 디코딩
        val = int(np.round(raw[0] / delta)) % self.params.t
        return val

    def add(self, ct1: Ciphertext, ct2: Ciphertext) -> Ciphertext:
        """`대상` 항목을 추가한다."""
        c0 = self._mod(ct1.c0 + ct2.c0)
        c1 = self._mod(ct1.c1 + ct2.c1)
        noise = ct1.noise_level + ct2.noise_level
        return Ciphertext(c0, c1, noise)

    def multiply_plain(self, ct: Ciphertext, scalar: int) -> Ciphertext:
        """``multiply_plain`` 동작을 수행한다."""
        c0 = self._mod(ct.c0 * scalar)
        c1 = self._mod(ct.c1 * scalar)
        return Ciphertext(c0, c1, ct.noise_level * abs(scalar))


class HomomorphicEncryption:
    """동형 암호 시뮬레이션."""

    def __init__(self, seed=42):
        """인스턴스를 초기화한다."""
        self.scheme = BGVScheme(seed=seed)
        self.rng = np.random.default_rng(seed)
        self.operations = 0
        self.correct = 0
        self.total = 0

    def test_addition(self, a: int, b: int) -> bool:
        """`addition` 결과를 계산하거나 판정한다."""
        ct_a = self.scheme.encrypt(a)
        ct_b = self.scheme.encrypt(b)
        ct_sum = self.scheme.add(ct_a, ct_b)
        result = self.scheme.decrypt(ct_sum)
        expected = (a + b) % self.scheme.params.t
        self.operations += 1
        self.total += 1
        if result == expected:
            self.correct += 1
            return True
        return False

    def test_scalar_mult(self, a: int, scalar: int) -> bool:
        """`scalar mult` 결과를 계산하거나 판정한다."""
        ct_a = self.scheme.encrypt(a)
        ct_prod = self.scheme.multiply_plain(ct_a, scalar)
        result = self.scheme.decrypt(ct_prod)
        expected = (a * scalar) % self.scheme.params.t
        self.operations += 1
        self.total += 1
        if result == expected:
            self.correct += 1
            return True
        return False

    def run_tests(self, n=20):
        """``run_tests`` 동작을 수행한다."""
        for _ in range(n):
            a = int(self.rng.integers(0, 50))
            b = int(self.rng.integers(0, 50))
            self.test_addition(a, b)
            self.test_scalar_mult(a, int(self.rng.integers(1, 5)))

    def summary(self):
        """현재 상태 요약을 반환한다."""
        return {
            "params_n": self.scheme.params.n,
            "params_q": self.scheme.params.q,
            "operations": self.operations,
            "correct": self.correct,
            "accuracy": round(self.correct / max(self.total, 1), 4),
        }


if __name__ == "__main__":
    he = HomomorphicEncryption(42)
    he.run_tests(20)
    for k, v in he.summary().items():
        print(f"  {k}: {v}")
