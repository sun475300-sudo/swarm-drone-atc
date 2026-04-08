"""
Transformer Trajectory Predictor (Phase 661)

이 모듈은 PyTorch를 사용하여 드론의 과거 궤적을 기반으로 향후 N-step 궤적을 예측하는
Transformer 기반 딥러닝 모델을 정의합니다.
"""
import torch
import torch.nn as nn
import numpy as np

class TrajectoryPredictor(nn.Module):
    def __init__(self, input_dim=3, d_model=64, nhead=4, num_layers=3, output_dim=3, seq_len=10, pred_len=5):
        """
        드론 궤적 예측을 위한 Transformer 모델.
        
        Args:
            input_dim: 입력 특징 차원 수 (기본: x, y, z = 3)
            d_model: 트랜스포머 은닉층 차원 (d_model)
            nhead: 멀티헤드 어텐션 헤드 수
            num_layers: 인코더/디코더 레이어 수
            output_dim: 출력 특징 차원 수 (x, y, z)
            seq_len: 과거 관측 시퀀스 길이
            pred_len: 예측할 미래 시퀀스 길이
        """
        super().__init__()
        self.input_dim = input_dim
        self.d_model = d_model
        self.seq_len = seq_len
        self.pred_len = pred_len
        
        # 입력 프로젝션 (Linear layer to expand dim)
        self.input_projection = nn.Linear(input_dim, d_model)
        
        # 위치 인코딩 (Positional Encoding)
        # 매우 단순한 형태의 학습 가능한 파라미터로 대체
        self.positional_encoding = nn.Parameter(torch.zeros(1, seq_len + pred_len, d_model))
        
        # Transformer 기반 인코더
        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead, batch_first=True)
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # 출력 프로젝션 (은닉 상태를 x, y, z로 매핑)
        self.output_projection = nn.Linear(d_model, output_dim)
        
    def forward(self, src):
        """
        Args:
            src: [batch_size, seq_len, input_dim] 형태의 텐서 (과거 궤적 데이터)
        Returns:
            [batch_size, pred_len, output_dim] 형태의 예측 결과
        """
        batch_size = src.size(0)
        
        # 입력 벡터 차원 확장
        x = self.input_projection(src) # [B, seq_len, d_model]
        
        # 위치 인코딩 추가
        x = x + self.positional_encoding[:, :self.seq_len, :]
        
        # Transformer 통과
        memory = self.transformer_encoder(x) # [B, seq_len, d_model]
        
        # 마지막 타임스텝의 출력을 바탕으로 향후 pred_len을 예측하는 단순한 디코딩
        # (실제 구현에서는 Auto-regressive 또는 Transformer Decoder를 쓸 수 있으나 시뮬레이션용으로 경량화)
        last_hidden = memory[:, -1, :].unsqueeze(1) # [B, 1, d_model]
        
        # pred_len만큼 복제 (단순 확장이지만 내부적으로 더 정교한 MLP를 붙일 수 있음)
        expanded_hidden = last_hidden.repeat(1, self.pred_len, 1) # [B, pred_len, d_model]
        
        # 미래 구간에 대한 위치 인코딩 합산
        expanded_hidden = expanded_hidden + self.positional_encoding[:, self.seq_len:, :]
        
        # 최종 프로젝션하여 x, y, z 획득
        out = self.output_projection(expanded_hidden) # [B, pred_len, output_dim]
        
        return out

def predict_trajectory_inference(model: TrajectoryPredictor, history_positions: list[tuple[float, float, float]]) -> list[tuple[float, float, float]]:
    """
    관제 시스템(AirspaceController)에서 호출하기 편한 추론 래퍼 함수.
    
    Args:
        model: 학습된 TrajectoryPredictor 인스턴스
        history_positions: 최근 관측된 드론 위치 [(x, y, z), ...] (길이는 model.seq_len이어야 함)
        
    Returns:
        예측된 미래 위치 [(x, y, z), ...] (길이는 model.pred_len)
    """
    if len(history_positions) < model.seq_len:
        # 패딩 처리: 입력 길이가 짧을 경우 첫 번째 위치로 채움
        pad_len = model.seq_len - len(history_positions)
        padded = [history_positions[0]] * pad_len + history_positions
    else:
        padded = history_positions[-model.seq_len:]
        
    # [1, seq_len, 3] Tensor 구성
    input_array = np.array(padded, dtype=np.float32)
    input_tensor = torch.tensor(input_array).unsqueeze(0)
    
    model.eval()
    with torch.no_grad():
        preds = model(input_tensor) # [1, pred_len, 3]
        
    pred_list = preds.squeeze(0).cpu().numpy().tolist()
    return [(float(p[0]), float(p[1]), float(p[2])) for p in pred_list]

if __name__ == "__main__":
    # Test stub
    model = TrajectoryPredictor(seq_len=10, pred_len=5)
    dummy_history = [
        (10.0 + i, 20.0 + i, 60.0) for i in range(10)
    ]
    preds = predict_trajectory_inference(model, dummy_history)
    print("Dummy 예측 결과:")
    for i, p in enumerate(preds):
        print(f"t+{i+1}: {p}")
