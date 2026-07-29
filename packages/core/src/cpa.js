import { dot, magnitude, scale, subtract, vector3 } from './vector.js';

export const DEFAULT_CPA_LOOKAHEAD_SECONDS = 12;

function stateVector(state, field) {
  if (!state || typeof state !== 'object') {
    throw new TypeError('state must be an object');
  }
  return vector3(state[field], `state.${field}`);
}

/**
 * Calculate the 3D closest point of approach between two constant-velocity states.
 */
export function closestPointOfApproach(
  own,
  other,
  lookaheadSeconds = DEFAULT_CPA_LOOKAHEAD_SECONDS,
) {
  if (!Number.isFinite(lookaheadSeconds) || lookaheadSeconds < 0) {
    throw new RangeError('lookaheadSeconds must be a finite non-negative number');
  }
  const ownPosition = stateVector(own, 'position');
  const otherPosition = stateVector(other, 'position');
  const ownVelocity = stateVector(own, 'velocity');
  const otherVelocity = stateVector(other, 'velocity');
  const relativePosition = subtract(ownPosition, otherPosition);
  const relativeVelocity = subtract(ownVelocity, otherVelocity);
  const relativeSpeedSquared = dot(relativeVelocity, relativeVelocity);
  const currentDistance = magnitude(relativePosition);
  const unconstrainedTime = relativeSpeedSquared > 1e-9
    ? -dot(relativePosition, relativeVelocity) / relativeSpeedSquared
    : 0;
  const timeSeconds = Math.max(0, Math.min(lookaheadSeconds, unconstrainedTime));
  const separation = [
    relativePosition[0] + relativeVelocity[0] * timeSeconds,
    relativePosition[1] + relativeVelocity[1] * timeSeconds,
    relativePosition[2] + relativeVelocity[2] * timeSeconds,
  ];
  const distanceAtCpa = magnitude(separation);
  const relativeSpeed = Math.sqrt(relativeSpeedSquared);
  const closingSpeed = currentDistance > 1e-9
    ? Math.max(0, -dot(relativePosition, relativeVelocity) / currentDistance)
    : relativeSpeed;

  return {
    timeSeconds,
    distance: distanceAtCpa,
    currentDistance,
    relativeSpeed,
    closingSpeed,
    converging: distanceAtCpa < currentDistance,
    ownPosition: [
      ownPosition[0] + ownVelocity[0] * timeSeconds,
      ownPosition[1] + ownVelocity[1] * timeSeconds,
      ownPosition[2] + ownVelocity[2] * timeSeconds,
    ],
    otherPosition: [
      otherPosition[0] + otherVelocity[0] * timeSeconds,
      otherPosition[1] + otherVelocity[1] * timeSeconds,
      otherPosition[2] + otherVelocity[2] * timeSeconds,
    ],
  };
}

/**
 * Return deterministic pairwise CPA conflicts in input order.
 */
export function findConflictPairs(
  states,
  {
    minimumSeparation = 100,
    lookaheadSeconds = DEFAULT_CPA_LOOKAHEAD_SECONDS,
    maxPairs = Number.POSITIVE_INFINITY,
  } = {},
) {
  if (!Array.isArray(states)) throw new TypeError('states must be an array');
  if (!Number.isFinite(minimumSeparation) || minimumSeparation < 0) {
    throw new RangeError('minimumSeparation must be a finite non-negative number');
  }
  if (!(maxPairs === Number.POSITIVE_INFINITY || (Number.isInteger(maxPairs) && maxPairs >= 0))) {
    throw new RangeError('maxPairs must be a non-negative integer or Infinity');
  }

  const conflicts = [];
  for (let i = 0; i < states.length; i += 1) {
    for (let j = i + 1; j < states.length; j += 1) {
      const cpa = closestPointOfApproach(states[i], states[j], lookaheadSeconds);
      if (cpa.converging && cpa.distance < minimumSeparation) {
        conflicts.push({
          firstIndex: i,
          secondIndex: j,
          firstId: states[i].id ?? states[i].droneId ?? String(i),
          secondId: states[j].id ?? states[j].droneId ?? String(j),
          ...cpa,
        });
        if (conflicts.length >= maxPairs) return conflicts;
      }
    }
  }
  return conflicts;
}
