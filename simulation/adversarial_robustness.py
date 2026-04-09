# Phase 533: Adversarial Robustness — FGSM/PGD Attack & Defense
"""
적대적 공격 시뮬레이션 및 방어:
FGSM, PGD 공격으로 드론 제어 신호 교란 → 적대적 훈련으로 방어.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum


class AttackType(Enum):
    FGSM = "fgsm"
    PGD = "pgd"
    NOISE = "noise"
    SPOOF = "spoof"


@dataclass
class AttackResult:
    attack_type: AttackType
    original_signal: np.ndarray
    perturbed_signal: np.ndarray
    perturbation_norm: float
    success: bool  # 공격이 오분류를 유발했는가


@dataclass
class DefenseResult:
    detected: int
    blocked: int
    bypassed: int
    accuracy_before: float
    accuracy_after: float


class SimpleClassifier:
    """간이 드론 신호 분류기 (2-layer)."""

    def __init__(self, input_dim=10, hidden=16, output_dim=3, seed=42):
        rng = np.random.default_rng(seed)
        self.w1 = rng.normal(0, 0.5, (input_dim, hidden))
        self.b1 = np.zeros(hidden)
        self.w2 = rng.normal(0, 0.5, (hidden, output_dim))
        self.b2 = np.zeros(output_dim)

    def forward(self, x: np.ndarray) -> np.ndarray:
        h = np.maximum(0, x @ self.w1 + self.b1)  # ReLU
        logits = h @ self.w2 + self.b2
        exp_l = np.exp(logits - logits.max())
        return exp_l / exp_l.sum()

    def predict(self, x: np.ndarray) -> int:
        return int(np.argmax(self.forward(x)))

    def loss_gradient(self, x: np.ndarray, target: int) -> np.ndarray:
        """크로스엔트로피 손실의 입력 그래디언트 (수치 미분)."""
        eps = 1e-4
        grad = np.zeros_like(x)
        probs = self.forward(x)
        base_loss = -np.log(probs[target] + 1e-8)
        for i in range(len(x)):
            x_p = x.copy()
            x_p[i] += eps
            probs_p = self.forward(x_p)
            loss_p = -np.log(probs_p[target] + 1e-8)
            grad[i] = (loss_p - base_loss) / eps
        return grad


class AdversarialAttacker:
    """적대적 공격 생성기."""

    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)

    def fgsm(self, model: SimpleClassifier, x: np.ndarray, target: int, epsilon=0.3) -> AttackResult:
        grad = model.loss_gradient(x, target)
        perturbation = epsilon * np.sign(grad)
        x_adv = x + perturbation
        original_pred = model.predict(x)
        adv_pred = model.predict(x_adv)
        return AttackResult(
            AttackType.FGSM, x, x_adv,
            float(np.linalg.norm(perturbation)),
            adv_pred != original_pred
        )

    def pgd(self, model: SimpleClassifier, x: np.ndarray, target: int,
            epsilon=0.3, steps=10, step_size=0.05) -> AttackResult:
        x_adv = x.copy()
        original_pred = model.predict(x)
        for _ in range(steps):
            grad = model.loss_gradient(x_adv, target)
            x_adv = x_adv + step_size * np.sign(grad)
            # 프로젝션: epsilon-ball 내로 제한
            delta = np.clip(x_adv - x, -epsilon, epsilon)
            x_adv = x + delta
        adv_pred = model.predict(x_adv)
        return AttackResult(
            AttackType.PGD, x, x_adv,
            float(np.linalg.norm(x_adv - x)),
            adv_pred != original_pred
        )

    def noise_attack(self, x: np.ndarray, sigma=0.5) -> np.ndarray:
        return x + self.rng.normal(0, sigma, x.shape)


class AdversarialDefender:
    """적대적 방어: 입력 정제 + 적대적 훈련."""

    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)

    def input_smoothing(self, x: np.ndarray, window=3) -> np.ndarray:
        """이동 평균으로 적대적 섭동 완화."""
        if len(x) < window:
            return x
        smoothed = np.convolve(x, np.ones(window) / window, mode='same')
        return smoothed

    def detect_adversarial(self, x_orig: np.ndarray, x_test: np.ndarray, threshold=0.5) -> bool:
        """입력 차이 기반 적대적 탐지."""
        return float(np.linalg.norm(x_test - x_orig)) > threshold

    def adversarial_training_step(self, model: SimpleClassifier, x: np.ndarray,
                                   target: int, epsilon=0.1, lr=0.01):
        """적대적 샘플로 모델 가중치 미세 조정 (1 step)."""
        grad = model.loss_gradient(x, target)
        x_adv = x + epsilon * np.sign(grad)
        # 간이 가중치 업데이트 (w1만)
        h = np.maximum(0, x_adv @ model.w1 + model.b1)
        probs = model.forward(x_adv)
        error = probs.copy()
        error[target] -= 1.0
        dw2 = np.outer(h, error)
        model.w2 -= lr * dw2


class AdversarialRobustness:
    """적대적 강건성 시뮬레이션 총괄."""

    def __init__(self, n_samples=50, seed=42):
        self.rng = np.random.default_rng(seed)
        self.model = SimpleClassifier(seed=seed)
        self.attacker = AdversarialAttacker(seed)
        self.defender = AdversarialDefender(seed)
        self.samples = self.rng.normal(0, 1, (n_samples, 10))
        self.labels = self.rng.integers(0, 3, n_samples)
        self.attack_results: list[AttackResult] = []

    def run_attacks(self, epsilon=0.3) -> dict:
        fgsm_success = 0
        pgd_success = 0
        for i in range(len(self.samples)):
            r1 = self.attacker.fgsm(self.model, self.samples[i], int(self.labels[i]), epsilon)
            r2 = self.attacker.pgd(self.model, self.samples[i], int(self.labels[i]), epsilon)
            self.attack_results.extend([r1, r2])
            if r1.success:
                fgsm_success += 1
            if r2.success:
                pgd_success += 1
        n = len(self.samples)
        return {
            "fgsm_success_rate": fgsm_success / n,
            "pgd_success_rate": pgd_success / n,
            "total_attacks": len(self.attack_results),
        }

    def run_defense(self) -> DefenseResult:
        detected = 0
        blocked = 0
        bypassed = 0
        correct_before = 0
        correct_after = 0
        for i in range(len(self.samples)):
            x = self.samples[i]
            true_label = int(self.labels[i])
            pred_before = self.model.predict(x)
            if pred_before == true_label:
                correct_before += 1

            # 방어 적용
            x_smooth = self.defender.input_smoothing(x)
            pred_after = self.model.predict(x_smooth)
            if pred_after == true_label:
                correct_after += 1

            # FGSM 공격 후 탐지
            ar = self.attacker.fgsm(self.model, x, true_label)
            if self.defender.detect_adversarial(x, ar.perturbed_signal):
                detected += 1
                blocked += 1
            elif ar.success:
                bypassed += 1

        n = len(self.samples)
        return DefenseResult(detected, blocked, bypassed,
                             correct_before / n, correct_after / n)

    def summary(self):
        attacks = self.run_attacks()
        defense = self.run_defense()
        return {
            "samples": len(self.samples),
            "fgsm_success_rate": attacks["fgsm_success_rate"],
            "pgd_success_rate": attacks["pgd_success_rate"],
            "detected": defense.detected,
            "blocked": defense.blocked,
            "accuracy_before": defense.accuracy_before,
            "accuracy_after": defense.accuracy_after,
        }


if __name__ == "__main__":
    ar = AdversarialRobustness(50, 42)
    s = ar.summary()
    for k, v in s.items():
        print(f"  {k}: {v}")
