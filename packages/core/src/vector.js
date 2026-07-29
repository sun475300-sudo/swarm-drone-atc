const EPSILON = 1e-9;

export function vector3(value, name = 'vector') {
  if (!value || typeof value.length !== 'number' || value.length !== 3) {
    throw new TypeError(`${name} must contain exactly three numbers`);
  }
  const result = [Number(value[0]), Number(value[1]), Number(value[2])];
  if (!result.every(Number.isFinite)) {
    throw new TypeError(`${name} must contain only finite numbers`);
  }
  return result;
}

export function add(a, b) {
  return [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
}

export function subtract(a, b) {
  return [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
}

export function scale(value, factor) {
  return [value[0] * factor, value[1] * factor, value[2] * factor];
}

export function dot(a, b) {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

export function magnitude(value) {
  return Math.hypot(value[0], value[1], value[2]);
}

export function normalize(value) {
  const length = magnitude(value);
  return length <= EPSILON ? [0, 0, 0] : scale(value, 1 / length);
}

export function clampMagnitude(value, maximum) {
  if (!Number.isFinite(maximum) || maximum < 0) {
    throw new RangeError('maximum magnitude must be a finite non-negative number');
  }
  const length = magnitude(value);
  return length > maximum && length > EPSILON
    ? scale(value, maximum / length)
    : [...value];
}

export function distance(a, b) {
  return magnitude(subtract(a, b));
}
