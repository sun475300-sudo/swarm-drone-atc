# Baseline: VO — Velocity Obstacle (Fiorini & Shiller 1998)

**Reference:** Fiorini, P., & Shiller, Z. (1998).
*Motion Planning in Dynamic Environments Using Velocity Obstacles.*
International Journal of Robotics Research, 17(7), 760-772.

**License:** Re-implement from paper (no canonical reference impl).

## What it is

VO predicts the set of velocities that would lead to collision within
a time horizon, then picks the velocity outside the obstacle (closest
to the preferred velocity).

VO is **the precursor** to ORCA. The differences vs ORCA:

- VO is non-cooperative (assumes other agents won't change velocity).
- VO has no theoretical guarantee of deadlock-free convergence.
- VO is faster per tick (no LP solve, just geometric containment test).

## Adapter contract

Same `BaselineAdapter` Protocol as `../orca/README.md`. Implement
`benchmarks/baselines/vo/adapter.py`.

## Recommended implementation

A clean-room VO is ~150 lines of NumPy. The core function:

```python
def velocity_obstacle(
    self_pos: np.ndarray,        # (3,)
    self_vel: np.ndarray,        # (3,)
    other_pos: np.ndarray,       # (N, 3)
    other_vel: np.ndarray,       # (N, 3)
    self_radius: float,
    other_radii: np.ndarray,     # (N,)
    horizon_s: float,
) -> set[np.ndarray]:
    """Return the velocity obstacle as a set of half-plane constraints."""
```

Then `pick_velocity(VO, preferred_velocity)` picks the closest
admissible velocity.

## Known limitations against this benchmark suite

VO inherits all of ORCA's limitations (see `../orca/README.md`) plus:

- **No reciprocity.** Two VO agents will both detour, doubling the
  detour cost. Expect lower PE than ORCA on dense scenarios.
- **More deadlocks.** Dense intersection (sc 02) is likely to deadlock
  on at least one seed.

VO is included as the "naive reactive" baseline to show that even
ORCA's reciprocity is a meaningful improvement, and that SDACS's
hybrid is more than just a slightly better VO.
