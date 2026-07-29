import assert from 'node:assert/strict';
import test from 'node:test';

import {
  APF_PARAMETERS,
  attractiveForce,
  closestPointOfApproach,
  computeTotalForce,
  droneRepulsiveForce,
  findConflictPairs,
  forceToVelocity,
} from '../src/index.js';

test('CPA predicts a head-on encounter', () => {
  const result = closestPointOfApproach(
    { position: [-10, 0, 0], velocity: [1, 0, 0] },
    { position: [10, 0, 0], velocity: [-1, 0, 0] },
  );
  assert.equal(result.timeSeconds, 10);
  assert.equal(result.distance, 0);
  assert.equal(result.converging, true);
  assert.equal(result.closingSpeed, 2);
});

test('CPA clamps prediction to the configured lookahead', () => {
  const result = closestPointOfApproach(
    { position: [-100, 0, 0], velocity: [1, 0, 0] },
    { position: [100, 0, 0], velocity: [-1, 0, 0] },
    12,
  );
  assert.equal(result.timeSeconds, 12);
  assert.equal(result.distance, 176);
});

test('conflict pairs are deterministic and bounded', () => {
  const states = [
    { id: 'A', position: [-10, 0, 0], velocity: [1, 0, 0] },
    { id: 'B', position: [10, 0, 0], velocity: [-1, 0, 0] },
    { id: 'C', position: [0, 200, 0], velocity: [0, 1, 0] },
  ];
  const pairs = findConflictPairs(states, { minimumSeparation: 5, maxPairs: 1 });
  assert.equal(pairs.length, 1);
  assert.deepEqual([pairs[0].firstId, pairs[0].secondId], ['A', 'B']);
});

test('attractive force is continuous at the 10m transition', () => {
  assert.deepEqual(attractiveForce([0, 0, 0], [10, 0, 0]), [10, 0, 0]);
  assert.deepEqual(attractiveForce([0, 0, 0], [20, 0, 0]), [10, 0, 0]);
});

test('drone repulsion points away and increases while closing', () => {
  const staticForce = droneRepulsiveForce(
    [10, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0],
  );
  const closingForce = droneRepulsiveForce(
    [10, 0, 0], [0, 0, 0], [-5, 0, 0], [0, 0, 0],
  );
  assert.ok(staticForce[0] > 0);
  assert.ok(closingForce[0] > staticForce[0]);
});

test('total force preserves input values and respects maxForce', () => {
  const state = { id: 'DR-001', position: [0, 0, 10], velocity: [0, 0, 0] };
  const original = structuredClone(state);
  const force = computeTotalForce({
    state,
    goal: [1000, 0, 60],
    parameters: { ...APF_PARAMETERS, maxForce: 3 },
  });
  assert.deepEqual(state, original);
  assert.ok(Math.hypot(...force) <= 3 + Number.EPSILON);
});

test('force-to-velocity clips speed without mutating inputs', () => {
  const velocity = [10, 0, 0];
  const force = [10, 0, 0];
  assert.deepEqual(forceToVelocity(velocity, force, 1, 12), [12, 0, 0]);
  assert.deepEqual(velocity, [10, 0, 0]);
  assert.deepEqual(force, [10, 0, 0]);
});

test('invalid vectors fail at the public boundary', () => {
  assert.throws(
    () => closestPointOfApproach(
      { position: [0, 0], velocity: [0, 0, 0] },
      { position: [0, 0, 0], velocity: [0, 0, 0] },
    ),
    /exactly three/,
  );
});
