# GPU Benchmark Report

## Backend Info

- **backend**: torch
- **device**: cuda:0
- **gpu**: NVIDIA GeForce RTX 5070 Ti
- **vram_gb**: 17.1
- **n_gpus**: 1
- **cudnn_benchmark**: True
- **tf32**: True
- **multi_gpu**: False

## Results

Each test averaged over 5 runs. CPU limited to 500 drones.

| Drones | CPU (ms) | GPU (ms) | Speedup |
|-------:|---------:|---------:|--------:|
| 50 | 9.45 | 10.41 | 0.91x |
| 100 | 36.05 | 15.28 | 2.36x |
| 200 | 144.51 | 30.39 | 4.76x |
| 500 | 1134.20 | 86.68 | 13.08x |
| 1000 | N/A | 151.07 | - |

*Generated with seed=42*
