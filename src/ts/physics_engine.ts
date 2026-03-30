/**
 * Phase 330: TypeScript 3D Physics Engine
 * WebGL-ready Verlet integration with collision response.
 * Type-safe rigid body simulation.
 */

// ── Vector3 ────────────────────────────────────────────────────────
class Vec3 {
  constructor(
    public x: number = 0,
    public y: number = 0,
    public z: number = 0
  ) {}

  add(o: Vec3): Vec3 {
    return new Vec3(this.x + o.x, this.y + o.y, this.z + o.z);
  }

  sub(o: Vec3): Vec3 {
    return new Vec3(this.x - o.x, this.y - o.y, this.z - o.z);
  }

  scale(s: number): Vec3 {
    return new Vec3(this.x * s, this.y * s, this.z * s);
  }

  dot(o: Vec3): number {
    return this.x * o.x + this.y * o.y + this.z * o.z;
  }

  length(): number {
    return Math.sqrt(this.dot(this));
  }

  normalize(): Vec3 {
    const len = this.length();
    return len > 1e-12 ? this.scale(1 / len) : new Vec3();
  }

  clone(): Vec3 {
    return new Vec3(this.x, this.y, this.z);
  }
}

// ── Rigid Body ─────────────────────────────────────────────────────
interface RigidBodyConfig {
  id: string;
  position?: Vec3;
  velocity?: Vec3;
  mass?: number;
  radius?: number;
  restitution?: number;
  dragCoeff?: number;
  isStatic?: boolean;
}

class RigidBody {
  readonly id: string;
  position: Vec3;
  prevPosition: Vec3;
  velocity: Vec3;
  acceleration: Vec3;
  mass: number;
  radius: number;
  restitution: number;
  dragCoeff: number;
  isStatic: boolean;

  constructor(config: RigidBodyConfig) {
    this.id = config.id;
    this.position = config.position?.clone() ?? new Vec3();
    this.prevPosition = this.position.clone();
    this.velocity = config.velocity?.clone() ?? new Vec3();
    this.acceleration = new Vec3();
    this.mass = config.mass ?? 2.0;
    this.radius = config.radius ?? 1.0;
    this.restitution = config.restitution ?? 0.5;
    this.dragCoeff = config.dragCoeff ?? 0.1;
    this.isStatic = config.isStatic ?? false;
  }
}

// ── Force Field ────────────────────────────────────────────────────
interface ForceField {
  name: string;
  direction: Vec3;
  strength: number;
  position?: Vec3; // undefined = uniform
  radius: number;
}

// ── Collision Info ─────────────────────────────────────────────────
interface CollisionInfo {
  bodyA: string;
  bodyB: string;
  contactPoint: Vec3;
  normal: Vec3;
  penetration: number;
  impulse: number;
}

// ── Physics Engine ─────────────────────────────────────────────────
class PhysicsEngine3D {
  private bodies = new Map<string, RigidBody>();
  private forces: ForceField[] = [];
  private collisions: CollisionInfo[] = [];
  private stepCount = 0;
  private dt: number;
  private boundsMin = new Vec3(-1000, -1000, 0);
  private boundsMax = new Vec3(1000, 1000, 500);

  constructor(dt: number = 0.01) {
    this.dt = dt;
    this.forces.push({
      name: "gravity",
      direction: new Vec3(0, 0, -9.81),
      strength: 1.0,
      radius: Infinity,
    });
  }

  addBody(body: RigidBody): void {
    this.bodies.set(body.id, body);
  }

  removeBody(id: string): boolean {
    return this.bodies.delete(id);
  }

  addForceField(force: ForceField): void {
    this.forces.push(force);
  }

  step(): void {
    this.collisions = [];
    const dt = this.dt;
    const dt2 = dt * dt;

    // Accumulate forces
    for (const body of this.bodies.values()) {
      if (body.isStatic) continue;
      body.acceleration = new Vec3();

      for (const ff of this.forces) {
        if (!ff.position) {
          body.acceleration = body.acceleration.add(ff.direction.scale(ff.strength));
        } else {
          const diff = ff.position.sub(body.position);
          const dist = diff.length();
          if (dist > 0 && dist < ff.radius) {
            body.acceleration = body.acceleration.add(
              diff.normalize().scale(ff.strength / Math.max(dist, 1))
            );
          }
        }
      }

      // Drag
      const speed = body.velocity.length();
      if (speed > 0.01) {
        const drag = body.velocity.scale(-body.dragCoeff * speed / body.mass);
        body.acceleration = body.acceleration.add(drag);
      }
    }

    // Verlet integration
    for (const body of this.bodies.values()) {
      if (body.isStatic) continue;
      const newPos = body.position
        .scale(2)
        .sub(body.prevPosition)
        .add(body.acceleration.scale(dt2));
      body.velocity = newPos.sub(body.position).scale(1 / dt);
      body.prevPosition = body.position.clone();
      body.position = newPos;
    }

    // Collision detection
    const dynamicBodies = [...this.bodies.values()].filter((b) => !b.isStatic);
    for (let i = 0; i < dynamicBodies.length; i++) {
      for (let j = i + 1; j < dynamicBodies.length; j++) {
        this.checkCollision(dynamicBodies[i], dynamicBodies[j]);
      }
    }

    // Boundary enforcement
    for (const body of this.bodies.values()) {
      if (body.isStatic) continue;
      for (const axis of ["x", "y", "z"] as const) {
        const idx = { x: 0, y: 1, z: 2 }[axis];
        const minB = [this.boundsMin.x, this.boundsMin.y, this.boundsMin.z][idx];
        const maxB = [this.boundsMax.x, this.boundsMax.y, this.boundsMax.z][idx];
        if ((body.position as any)[axis] < minB + body.radius) {
          (body.position as any)[axis] = minB + body.radius;
          (body.velocity as any)[axis] =
            Math.abs((body.velocity as any)[axis]) * body.restitution;
        } else if ((body.position as any)[axis] > maxB - body.radius) {
          (body.position as any)[axis] = maxB - body.radius;
          (body.velocity as any)[axis] =
            -Math.abs((body.velocity as any)[axis]) * body.restitution;
        }
      }
    }

    this.stepCount++;
  }

  private checkCollision(a: RigidBody, b: RigidBody): void {
    const diff = b.position.sub(a.position);
    const dist = diff.length();
    const minDist = a.radius + b.radius;

    if (dist < minDist && dist > 1e-6) {
      const normal = diff.normalize();
      const penetration = minDist - dist;
      const totalMass = a.mass + b.mass;

      a.position = a.position.sub(normal.scale((penetration * b.mass) / totalMass));
      b.position = b.position.add(normal.scale((penetration * a.mass) / totalMass));

      const relVel = a.velocity.sub(b.velocity);
      const velAlongNormal = relVel.dot(normal);
      if (velAlongNormal > 0) return;

      const e = Math.min(a.restitution, b.restitution);
      const j = (-(1 + e) * velAlongNormal) / (1 / a.mass + 1 / b.mass);

      a.velocity = a.velocity.add(normal.scale(j / a.mass));
      b.velocity = b.velocity.sub(normal.scale(j / b.mass));

      this.collisions.push({
        bodyA: a.id,
        bodyB: b.id,
        contactPoint: a.position.add(b.position).scale(0.5),
        normal,
        penetration,
        impulse: Math.abs(j),
      });
    }
  }

  runFor(durationSec: number): void {
    const steps = Math.floor(durationSec / this.dt);
    for (let i = 0; i < steps; i++) this.step();
  }

  getBody(id: string): RigidBody | undefined {
    return this.bodies.get(id);
  }

  getKineticEnergy(): number {
    let total = 0;
    for (const b of this.bodies.values()) {
      if (!b.isStatic) total += 0.5 * b.mass * b.velocity.dot(b.velocity);
    }
    return total;
  }

  summary(): Record<string, unknown> {
    return {
      totalBodies: this.bodies.size,
      staticBodies: [...this.bodies.values()].filter((b) => b.isStatic).length,
      forceFields: this.forces.length,
      stepCount: this.stepCount,
      collisionsLastStep: this.collisions.length,
      kineticEnergy: this.getKineticEnergy().toFixed(4),
    };
  }
}

// ── Main ───────────────────────────────────────────────────────────
function main(): void {
  const engine = new PhysicsEngine3D(0.01);

  engine.addBody(
    new RigidBody({
      id: "ball1",
      position: new Vec3(0, 0, 100),
      velocity: new Vec3(5, 0, 0),
      mass: 2,
      radius: 1,
    })
  );

  engine.addBody(
    new RigidBody({
      id: "ball2",
      position: new Vec3(20, 0, 100),
      velocity: new Vec3(-5, 0, 0),
      mass: 2,
      radius: 1,
    })
  );

  engine.runFor(1.0);

  console.log("Summary:", JSON.stringify(engine.summary(), null, 2));

  const b1 = engine.getBody("ball1");
  if (b1) {
    console.log(`Ball1 pos: (${b1.position.x.toFixed(2)}, ${b1.position.y.toFixed(2)}, ${b1.position.z.toFixed(2)})`);
  }
}

main();

export { PhysicsEngine3D, RigidBody, Vec3, ForceField, CollisionInfo };
