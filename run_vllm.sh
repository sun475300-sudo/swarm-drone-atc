#!/bin/bash
# 관제 AI용 vLLM 서버 — 응답 속도 최우선

MODEL=${1:-"Qwen/Qwen2.5-7B-Instruct"}
PORT=${2:-8000}

echo "=== JARVIS vLLM 서버 시작 ==="
echo "모델: $MODEL"
echo "포트: $PORT"

vllm serve "$MODEL" \
    --host 0.0.0.0 \
    --port "$PORT" \
    --max-model-len 2048 \
    --gpu-memory-utilization 0.85 \
    --dtype half \
    --max-num-seqs 16

# 모델 선택 가이드:
# VRAM 절약 (8GB): Qwen/Qwen2.5-7B-Instruct-AWQ
# 기본 추천 (14GB): Qwen/Qwen2.5-7B-Instruct
# 한국어 특화 (16GB): LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct
