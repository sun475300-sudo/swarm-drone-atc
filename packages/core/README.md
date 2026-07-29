# `@sdacs/core`

Dependency-free ECMAScript modules for SDACS collision prediction and
artificial-potential-field avoidance. The formulas and default parameters are
aligned with `simulation/apf_engine/apf.py`.

```js
import {
  closestPointOfApproach,
  computeTotalForce,
} from '@sdacs/core';

const cpa = closestPointOfApproach(
  { position: [0, 0, 60], velocity: [10, 0, 0] },
  { position: [100, 0, 60], velocity: [-10, 0, 0] },
);

const force = computeTotalForce({
  state: { id: 'DR-001', position: [0, 0, 60], velocity: [10, 0, 0] },
  goal: [1000, 0, 60],
  neighbors: [],
  obstacles: [],
});
```

All functions are pure: inputs are validated and never mutated. Coordinates
and velocities use SI units (`m`, `m/s`), and vectors are `[x, y, z]`.

## Local verification

```bash
npm test
npm pack --dry-run
```

Registry publication remains a release-manager action requiring npm
provenance and the `@sdacs` organization.
