# GPU Benchmark Report

## Backend Info

- **backend**: torch
- **device**: cuda
- **gpu**: NVIDIA GeForce RTX 5070 Ti
- **vram_gb**: 17.1

## Results

Each test averaged over 5 runs. CPU limited to 500 drones.

| Drones | CPU (ms) | GPU (ms) | Speedup |
|-------:|---------:|---------:|--------:|
| 50 | 11.19 | 13.04 | 0.86x |
| 100 | 42.74 | 18.06 | 2.37x |
| 200 | 188.68 | 28.13 | 6.71x |
| 500 | 1192.47 | 97.57 | 12.22x |
| 1000 | N/A | 193.95 | - |

*Generated with seed=42*
