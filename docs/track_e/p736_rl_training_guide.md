# P736 RL 충돌 회피 학습 가이드

`src/rl/ppo_collision.py` 스켈레톤을 실제 학습으로 진행하는 가이드.

## 환경 요구사항

- Python 3.10+
- PyTorch 2.x (CUDA 권장)
- stable-baselines3
- gymnasium
- GPU: NVIDIA RTX 3060+ 또는 Colab Pro

## 설치

```bash
pip install stable-baselines3[extra] gymnasium tensorboard
```

## 학습

```bash
# 베이스라인 (50k step ~ 30분 GPU)
python -m src.rl.ppo_collision train \
    --steps 50000 \
    --scenario default \
    --n-drones 50 \
    --output models/ppo_v1.zip

# 대규모 학습 (500k step ~ 5시간)
python -m src.rl.ppo_collision train \
    --steps 500000 \
    --scenario high_density \
    --n-drones 150 \
    --output models/ppo_large.zip \
    --tensorboard logs/ppo_large/
```

## 평가

```bash
# 10 시나리오 × 5 seed
python -m src.rl.ppo_collision eval \
    --model models/ppo_v1.zip \
    --scenarios 10 --seeds 5 \
    --baseline orca,vo,cbs \
    --output results/rl_vs_baseline.csv

# 메트릭 비교
python scripts/compare_baselines.py \
    --algorithms ppo,sdacs,orca \
    --metrics NMR,MSD,AU,RTF
```

## 기대 결과

- ORCA 대비 NMR 동등 또는 -10%
- AU +25% (학습된 정책의 효율적 회피)
- RTF 60x+ (실시간 가능)
- 일반화: 학습 시 unseen 시나리오에서도 NMR < 0.15

## 후속 (Sim-to-Real)

P739 Domain Randomization wrapper 활용:

```python
from src.training.domain_rand import DomainRandomizer, DomainConfig

cfg = DomainConfig(wind_speed_range=(0, 12))
rng = DomainRandomizer(cfg, seed=42)

env = SDACSGymEnv(scenario='default', n_drones=50)
env = DomainRandomizationWrapper(env, randomizer=rng)

# 학습 시 매 episode 도메인 랜덤화
model.learn(env, total_timesteps=500_000)
```

## Reward Shaping (참고)

```python
def compute_reward(state, action, next_state):
    r = 0
    # 안전: near_miss/collision penalty
    r -= 1.0 * next_state['near_miss_count']
    r -= 10.0 * next_state['collision_count']
    # 진행: goal 가까이
    r += 0.1 * (state['dist_to_goal'] - next_state['dist_to_goal'])
    # 에너지: action norm penalty
    r -= 0.001 * np.linalg.norm(action)
    # 시간: step penalty
    r -= 0.01
    return r
```
