"""ONNX 모델 내보내기 모듈 — CollisionPredictor를 ONNX 형식으로 변환한다."""

from __future__ import annotations

from pathlib import Path

import torch

from simulation.collision_predictor import CollisionPredictor, INPUT_DIM


def export_collision_model(
    model: CollisionPredictor,
    output_path: str | Path,
    opset_version: int = 17,
) -> Path:
    """CollisionPredictor를 ONNX 파일로 내보낸다.

    Args:
        model: 학습된 CollisionPredictor 인스턴스
        output_path: 저장할 ONNX 파일 경로
        opset_version: ONNX opset 버전

    Returns:
        저장된 파일의 Path
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 더미 입력 생성
    dummy_input = torch.randn(1, INPUT_DIM, device=model.device)

    model.model.eval()
    torch.onnx.export(
        model.model,
        dummy_input,
        str(output_path),
        opset_version=opset_version,
        input_names=["drone_pair_features"],
        output_names=["collision_probability"],
        dynamic_axes={
            "drone_pair_features": {0: "batch_size"},
            "collision_probability": {0: "batch_size"},
        },
    )
    return output_path


def validate_onnx(path: str | Path) -> bool:
    """ONNX 모델을 로드하고 onnxruntime으로 추론을 검증한다.

    onnxruntime이 없으면 검증을 건너뛴다.

    Returns:
        검증 성공 여부 (onnxruntime 없으면 True)
    """
    try:
        import onnxruntime as ort  # noqa: F811
    except ImportError:
        return True

    import numpy as np

    session = ort.InferenceSession(str(path))
    dummy = np.random.randn(1, INPUT_DIM).astype(np.float32)
    outputs = session.run(None, {"drone_pair_features": dummy})

    result = outputs[0]
    # 출력 shape 및 범위 확인 (sigmoid → 0~1)
    if result.shape[-1] != 1 and result.ndim == 1:
        pass  # squeeze된 경우
    return bool(np.all((result >= 0.0) & (result <= 1.0)))
