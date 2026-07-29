import {
  add,
  clampMagnitude,
  distance,
  dot,
  magnitude,
  normalize,
  scale,
  subtract,
  vector3,
} from './vector.js';

export const APF_PARAMETERS = Object.freeze({
  kAtt: 1,
  kRepDrone: 2.5,
  kRepObstacle: 5,
  droneInfluenceDistance: 50,
  obstacleInfluenceDistance: 30,
  maxForce: 10,
  altitudeGain: 0.5,
  targetAltitude: 60,
});

export const APF_PARAMETERS_WINDY = Object.freeze({
  kAtt: 1,
  kRepDrone: 6.5,
  kRepObstacle: 7,
  droneInfluenceDistance: 80,
  obstacleInfluenceDistance: 45,
  maxForce: 22,
  altitudeGain: 1,
  targetAltitude: 60,
});

export const APF_PARAMETERS_HIGH_DENSITY = Object.freeze({
  kAtt: 0.3,
  kRepDrone: 30,
  kRepObstacle: 15,
  droneInfluenceDistance: 250,
  obstacleInfluenceDistance: 100,
  maxForce: 50,
  altitudeGain: 5,
  targetAltitude: 60,
});

function validateGain(value, name) {
  if (!Number.isFinite(value) || value < 0) {
    throw new RangeError(`${name} must be a finite non-negative number`);
  }
}

function repulsiveForce(ownPosition, sourcePosition, kRep, influenceDistance) {
  validateGain(kRep, 'kRep');
  validateGain(influenceDistance, 'influenceDistance');
  const difference = subtract(ownPosition, sourcePosition);
  const separation = magnitude(difference);
  if (separation < 1e-3 || separation >= influenceDistance) return [0, 0, 0];
  const strength = kRep
    * (1 / separation - 1 / influenceDistance)
    / (separation ** 2);
  return scale(normalize(difference), strength);
}

export function attractiveForce(position, goal, kAtt = APF_PARAMETERS.kAtt) {
  const ownPosition = vector3(position, 'position');
  const target = vector3(goal, 'goal');
  validateGain(kAtt, 'kAtt');
  const difference = subtract(target, ownPosition);
  const separation = magnitude(difference);
  if (separation < 0.1) return [0, 0, 0];
  return separation <= 10
    ? scale(difference, kAtt)
    : scale(normalize(difference), kAtt * 10);
}

export function droneRepulsiveForce(
  ownPosition,
  otherPosition,
  ownVelocity,
  otherVelocity,
  kRep = APF_PARAMETERS.kRepDrone,
  influenceDistance = APF_PARAMETERS.droneInfluenceDistance,
) {
  const ownPos = vector3(ownPosition, 'ownPosition');
  const otherPos = vector3(otherPosition, 'otherPosition');
  const ownVel = vector3(ownVelocity, 'ownVelocity');
  const otherVel = vector3(otherVelocity, 'otherVelocity');
  let force = repulsiveForce(ownPos, otherPos, kRep, influenceDistance);
  if (magnitude(force) === 0) return force;

  const normal = normalize(subtract(ownPos, otherPos));
  const closingSpeed = -dot(subtract(ownVel, otherVel), normal);
  if (closingSpeed > 0) {
    const maximumAmplification = influenceDistance > 100 ? 5 : 3;
    const amplification = Math.min(1 + closingSpeed / 3, maximumAmplification);
    force = scale(force, amplification);
  }
  return force;
}

export function obstacleRepulsiveForce(
  position,
  obstaclePosition,
  kRep = APF_PARAMETERS.kRepObstacle,
  influenceDistance = APF_PARAMETERS.obstacleInfluenceDistance,
) {
  return repulsiveForce(
    vector3(position, 'position'),
    vector3(obstaclePosition, 'obstaclePosition'),
    kRep,
    influenceDistance,
  );
}

function blendParameters(first, second, ratio) {
  return Object.fromEntries(
    Object.keys(first).map((key) => [key, first[key] * (1 - ratio) + second[key] * ratio]),
  );
}

export function selectApfParameters(state, neighbors = [], windSpeed = 0) {
  const position = vector3(state.position, 'state.position');
  if (!Array.isArray(neighbors)) throw new TypeError('neighbors must be an array');
  if (!Number.isFinite(windSpeed) || windSpeed < 0) {
    throw new RangeError('windSpeed must be a finite non-negative number');
  }
  const nearby = neighbors.filter(
    (neighbor) => distance(position, vector3(neighbor.position, 'neighbor.position')) < 150,
  ).length;
  if (nearby >= 2) return { ...APF_PARAMETERS_HIGH_DENSITY };
  if (windSpeed > 12) return { ...APF_PARAMETERS_WINDY };
  if (windSpeed > 6) {
    return blendParameters(APF_PARAMETERS, APF_PARAMETERS_WINDY, (windSpeed - 6) / 6);
  }
  return { ...APF_PARAMETERS };
}

function deterministicSign(identifier) {
  let hash = 2166136261;
  for (const character of String(identifier ?? '')) {
    hash ^= character.codePointAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0) % 2 === 0 ? 1 : -1;
}

export function computeTotalForce({
  state,
  goal,
  neighbors = [],
  obstacles = [],
  parameters,
  windSpeed = 0,
}) {
  if (!state || typeof state !== 'object') throw new TypeError('state must be an object');
  if (!Array.isArray(neighbors)) throw new TypeError('neighbors must be an array');
  if (!Array.isArray(obstacles)) throw new TypeError('obstacles must be an array');
  const position = vector3(state.position, 'state.position');
  const velocity = vector3(state.velocity, 'state.velocity');
  const target = vector3(goal, 'goal');
  const params = parameters
    ? { ...APF_PARAMETERS, ...parameters }
    : selectApfParameters(state, neighbors, windSpeed);

  let total = attractiveForce(position, target, params.kAtt);
  for (const neighbor of neighbors) {
    total = add(total, droneRepulsiveForce(
      position,
      neighbor.position,
      velocity,
      neighbor.velocity,
      params.kRepDrone,
      params.droneInfluenceDistance,
    ));
  }
  for (const obstacle of obstacles) {
    total = add(total, obstacleRepulsiveForce(
      position,
      obstacle,
      params.kRepObstacle,
      params.obstacleInfluenceDistance,
    ));
  }

  total[2] += params.altitudeGain * (params.targetAltitude - position[2]);
  if (position[2] < 5) {
    total[2] += params.kRepObstacle * (1 / Math.max(position[2], 0.1) - 1 / 5);
  }

  const goalDistance = distance(target, position);
  if (magnitude(total) < 0.5 && goalDistance > 20) {
    const goalDirection = normalize(subtract(target, position));
    let perpendicular = normalize([-goalDirection[1], goalDirection[0], 0]);
    if (magnitude(perpendicular) < 1e-3) perpendicular = [1, 0, 0];
    total = add(
      total,
      scale(perpendicular, deterministicSign(state.id ?? state.droneId) * params.kAtt * 2),
    );
  }
  return clampMagnitude(total, params.maxForce);
}

export function forceToVelocity(
  currentVelocity,
  force,
  deltaSeconds,
  maxSpeed = 15,
) {
  const velocity = vector3(currentVelocity, 'currentVelocity');
  const acceleration = vector3(force, 'force');
  if (!Number.isFinite(deltaSeconds) || deltaSeconds < 0) {
    throw new RangeError('deltaSeconds must be a finite non-negative number');
  }
  validateGain(maxSpeed, 'maxSpeed');
  return clampMagnitude(add(velocity, scale(acceleration, deltaSeconds)), maxSpeed);
}
