export type Vector3 = readonly [number, number, number];

export interface MotionState {
  id?: string;
  droneId?: string;
  position: Vector3;
  velocity: Vector3;
}

export interface CpaResult {
  timeSeconds: number;
  distance: number;
  currentDistance: number;
  relativeSpeed: number;
  closingSpeed: number;
  converging: boolean;
  ownPosition: Vector3;
  otherPosition: Vector3;
}

export interface ConflictPair extends CpaResult {
  firstIndex: number;
  secondIndex: number;
  firstId: string;
  secondId: string;
}

export interface ApfParameters {
  kAtt: number;
  kRepDrone: number;
  kRepObstacle: number;
  droneInfluenceDistance: number;
  obstacleInfluenceDistance: number;
  maxForce: number;
  altitudeGain: number;
  targetAltitude: number;
}

export const DEFAULT_CPA_LOOKAHEAD_SECONDS: number;
export const APF_PARAMETERS: Readonly<ApfParameters>;
export const APF_PARAMETERS_WINDY: Readonly<ApfParameters>;
export const APF_PARAMETERS_HIGH_DENSITY: Readonly<ApfParameters>;

export function closestPointOfApproach(
  own: MotionState,
  other: MotionState,
  lookaheadSeconds?: number,
): CpaResult;

export function findConflictPairs(
  states: readonly MotionState[],
  options?: {
    minimumSeparation?: number;
    lookaheadSeconds?: number;
    maxPairs?: number;
  },
): ConflictPair[];

export function attractiveForce(
  position: Vector3,
  goal: Vector3,
  kAtt?: number,
): Vector3;

export function droneRepulsiveForce(
  ownPosition: Vector3,
  otherPosition: Vector3,
  ownVelocity: Vector3,
  otherVelocity: Vector3,
  kRep?: number,
  influenceDistance?: number,
): Vector3;

export function obstacleRepulsiveForce(
  position: Vector3,
  obstaclePosition: Vector3,
  kRep?: number,
  influenceDistance?: number,
): Vector3;

export function selectApfParameters(
  state: MotionState,
  neighbors?: readonly MotionState[],
  windSpeed?: number,
): ApfParameters;

export function computeTotalForce(options: {
  state: MotionState;
  goal: Vector3;
  neighbors?: readonly MotionState[];
  obstacles?: readonly Vector3[];
  parameters?: Partial<ApfParameters>;
  windSpeed?: number;
}): Vector3;

export function forceToVelocity(
  currentVelocity: Vector3,
  force: Vector3,
  deltaSeconds: number,
  maxSpeed?: number,
): Vector3;
