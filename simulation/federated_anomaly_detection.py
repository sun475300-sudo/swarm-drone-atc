# Phase 547: Federated Anomaly Detection — Distributed Learning
"""
연합학습 기반 분산 이상탐지: 각 드론이 로컬 모델 훈련 후
중앙 서버에서 가중치 집계(FedAvg). 프라이버시 보존.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class LocalModel:
    node_id: str
    weights: np.ndarray
    bias: np.ndarray
    n_samples: int = 0
    local_loss: float = 0.0


@dataclass
class FederatedRound:
    round_id: int
    participants: int
    global_loss: float
    anomalies_detected: int


class AnomalyDetector:
    """간이 오토인코더 기반 이상탐지."""

    def __init__(self, input_dim=8, hidden=4, seed=42):
        rng = np.random.default_rng(seed)
        self.w_enc = rng.normal(0, 0.3, (input_dim, hidden))
        self.b_enc = np.zeros(hidden)
        self.w_dec = rng.normal(0, 0.3, (hidden, input_dim))
        self.b_dec = np.zeros(input_dim)
        self.threshold = 1.0

    def encode(self, x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x @ self.w_enc + self.b_enc)

    def decode(self, h: np.ndarray) -> np.ndarray:
        return h @ self.w_dec + self.b_dec

    def reconstruction_error(self, x: np.ndarray) -> float:
        h = self.encode(x)
        x_hat = self.decode(h)
        return float(np.mean((x - x_hat) ** 2))

    def is_anomaly(self, x: np.ndarray) -> bool:
        return self.reconstruction_error(x) > self.threshold

    def train_step(self, x_batch: np.ndarray, lr=0.01):
        for x in x_batch:
            h = self.encode(x)
            x_hat = self.decode(h)
            error = x_hat - x
            # 역전파 (간이)
            dw_dec = np.outer(h, error)
            db_dec = error
            dh = error @ self.w_dec.T
            dh[h <= 0] = 0
            dw_enc = np.outer(x, dh)
            db_enc = dh
            self.w_dec -= lr * dw_dec
            self.b_dec -= lr * db_dec
            self.w_enc -= lr * dw_enc
            self.b_enc -= lr * db_enc

    def get_params(self):
        return (self.w_enc.copy(), self.b_enc.copy(), self.w_dec.copy(), self.b_dec.copy())

    def set_params(self, params):
        self.w_enc, self.b_enc, self.w_dec, self.b_dec = params


class FederatedServer:
    """FedAvg 중앙 서버."""

    def __init__(self, input_dim=8, hidden=4, seed=42):
        self.global_model = AnomalyDetector(input_dim, hidden, seed)
        self.rounds: list[FederatedRound] = []

    def aggregate(self, local_models: list[LocalModel]):
        """가중 평균으로 글로벌 모델 업데이트."""
        total_samples = sum(m.n_samples for m in local_models)
        if total_samples == 0:
            return

        new_w_enc = np.zeros_like(self.global_model.w_enc)
        new_b_enc = np.zeros_like(self.global_model.b_enc)
        new_w_dec = np.zeros_like(self.global_model.w_dec)
        new_b_dec = np.zeros_like(self.global_model.b_dec)

        for m in local_models:
            w = m.n_samples / total_samples
            # weights/bias가 LocalModel에 저장
            new_w_enc += w * m.weights[:self.global_model.w_enc.size].reshape(self.global_model.w_enc.shape)

        # 간이: 첫 번째 모델의 구조로 평균
        params_list = []
        for m in local_models:
            # LocalModel.weights에 flatten된 파라미터
            params_list.append((m.weights, m.n_samples))

        if params_list:
            avg = np.average([p[0] for p in params_list],
                             weights=[p[1] for p in params_list], axis=0)
            # 글로벌 모델에 할당
            offset = 0
            s = self.global_model.w_enc.size
            self.global_model.w_enc = avg[offset:offset+s].reshape(self.global_model.w_enc.shape)
            offset += s
            s = self.global_model.b_enc.size
            self.global_model.b_enc = avg[offset:offset+s]
            offset += s
            s = self.global_model.w_dec.size
            self.global_model.w_dec = avg[offset:offset+s].reshape(self.global_model.w_dec.shape)
            offset += s
            s = self.global_model.b_dec.size
            self.global_model.b_dec = avg[offset:offset+s]


class FederatedAnomalyDetection:
    """연합 이상탐지 시뮬레이션."""

    def __init__(self, n_clients=8, n_samples_per_client=30, seed=42):
        self.rng = np.random.default_rng(seed)
        self.n_clients = n_clients
        self.input_dim = 8
        self.hidden = 4
        self.server = FederatedServer(self.input_dim, self.hidden, seed)
        self.client_data: list[np.ndarray] = []
        self.anomaly_data: np.ndarray = self.rng.normal(5, 2, (10, self.input_dim))
        self.rounds: list[FederatedRound] = []

        # 클라이언트별 정상 데이터 생성
        for i in range(n_clients):
            data = self.rng.normal(0, 1, (n_samples_per_client, self.input_dim))
            self.client_data.append(data)

    def train_round(self) -> FederatedRound:
        local_models = []
        for i in range(self.n_clients):
            # 글로벌 모델 복제 → 로컬 훈련
            detector = AnomalyDetector(self.input_dim, self.hidden, seed=i)
            detector.set_params(self.server.global_model.get_params())
            detector.train_step(self.client_data[i], lr=0.01)

            # flatten params
            params = detector.get_params()
            flat = np.concatenate([p.flatten() for p in params])
            lm = LocalModel(f"client_{i}", flat, np.zeros(1), len(self.client_data[i]),
                            detector.reconstruction_error(self.client_data[i][0]))
            local_models.append(lm)

        self.server.aggregate(local_models)

        # 이상 탐지 평가
        detected = sum(1 for x in self.anomaly_data if self.server.global_model.is_anomaly(x))
        gl = float(np.mean([m.local_loss for m in local_models]))
        fr = FederatedRound(len(self.rounds), self.n_clients, gl, detected)
        self.rounds.append(fr)
        return fr

    def train(self, n_rounds=5):
        for _ in range(n_rounds):
            self.train_round()

    def summary(self):
        last = self.rounds[-1] if self.rounds else None
        return {
            "clients": self.n_clients,
            "rounds": len(self.rounds),
            "anomalies_detected": last.anomalies_detected if last else 0,
            "global_loss": round(last.global_loss, 4) if last else 0,
            "total_anomaly_samples": len(self.anomaly_data),
        }


if __name__ == "__main__":
    fad = FederatedAnomalyDetection(8, 30, 42)
    fad.train(5)
    for k, v in fad.summary().items():
        print(f"  {k}: {v}")
