// Phase 310: V Language Swarm Behavior Engine
// Reynolds Boids implementation with V's simplicity and performance.
// Separation, Alignment, Cohesion + Obstacle Avoidance.

module swarm_behavior

import math

// ── Types ────────────────────────────────────────────────────────
struct Vec3 {
pub mut:
	x f64
	y f64
	z f64
}

fn (a Vec3) add(b Vec3) Vec3 {
	return Vec3{a.x + b.x, a.y + b.y, a.z + b.z}
}

fn (a Vec3) sub(b Vec3) Vec3 {
	return Vec3{a.x - b.x, a.y - b.y, a.z - b.z}
}

fn (v Vec3) scale(s f64) Vec3 {
	return Vec3{v.x * s, v.y * s, v.z * s}
}

fn (v Vec3) length() f64 {
	return math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z)
}

fn (v Vec3) normalize() Vec3 {
	l := v.length()
	if l < 1e-12 {
		return Vec3{0, 0, 0}
	}
	return v.scale(1.0 / l)
}

fn (a Vec3) distance(b Vec3) f64 {
	return a.sub(b).length()
}

// ── Boid Agent ──────────────────────────────────────────────────
struct BoidAgent {
pub mut:
	id         int
	position   Vec3
	velocity   Vec3
	max_speed  f64 = 15.0
	max_force  f64 = 3.0
}

// ── Boid Parameters ─────────────────────────────────────────────
struct BoidParams {
pub:
	separation_radius f64 = 25.0
	alignment_radius  f64 = 50.0
	cohesion_radius   f64 = 50.0
	separation_weight f64 = 1.5
	alignment_weight  f64 = 1.0
	cohesion_weight   f64 = 1.0
	avoidance_weight  f64 = 2.0
	bounds_min        Vec3 = Vec3{-500, -500, 0}
	bounds_max        Vec3 = Vec3{500, 500, 200}
}

// ── Swarm Behavior Engine ───────────────────────────────────────
struct SwarmBehaviorEngine {
pub mut:
	agents    []BoidAgent
	params    BoidParams
	obstacles []Vec3
	step_count int
}

fn new_swarm_engine(params BoidParams) SwarmBehaviorEngine {
	return SwarmBehaviorEngine{
		agents: []BoidAgent{}
		params: params
		obstacles: []Vec3{}
		step_count: 0
	}
}

fn (mut e SwarmBehaviorEngine) add_agent(id int, pos Vec3, vel Vec3) {
	e.agents << BoidAgent{
		id: id
		position: pos
		velocity: vel
	}
}

fn (mut e SwarmBehaviorEngine) add_obstacle(pos Vec3) {
	e.obstacles << pos
}

// ── Core Boid Rules ─────────────────────────────────────────────
fn (e &SwarmBehaviorEngine) separation(agent &BoidAgent) Vec3 {
	mut steer := Vec3{0, 0, 0}
	mut count := 0
	for other in e.agents {
		if other.id == agent.id {
			continue
		}
		d := agent.position.distance(other.position)
		if d > 0 && d < e.params.separation_radius {
			diff := agent.position.sub(other.position).normalize().scale(1.0 / d)
			steer = steer.add(diff)
			count++
		}
	}
	if count > 0 {
		steer = steer.scale(1.0 / f64(count))
	}
	return steer
}

fn (e &SwarmBehaviorEngine) alignment(agent &BoidAgent) Vec3 {
	mut avg_vel := Vec3{0, 0, 0}
	mut count := 0
	for other in e.agents {
		if other.id == agent.id {
			continue
		}
		d := agent.position.distance(other.position)
		if d < e.params.alignment_radius {
			avg_vel = avg_vel.add(other.velocity)
			count++
		}
	}
	if count > 0 {
		avg_vel = avg_vel.scale(1.0 / f64(count))
		return avg_vel.sub(agent.velocity)
	}
	return Vec3{0, 0, 0}
}

fn (e &SwarmBehaviorEngine) cohesion(agent &BoidAgent) Vec3 {
	mut center := Vec3{0, 0, 0}
	mut count := 0
	for other in e.agents {
		if other.id == agent.id {
			continue
		}
		d := agent.position.distance(other.position)
		if d < e.params.cohesion_radius {
			center = center.add(other.position)
			count++
		}
	}
	if count > 0 {
		center = center.scale(1.0 / f64(count))
		return center.sub(agent.position)
	}
	return Vec3{0, 0, 0}
}

fn (e &SwarmBehaviorEngine) obstacle_avoidance(agent &BoidAgent) Vec3 {
	mut steer := Vec3{0, 0, 0}
	for obs in e.obstacles {
		d := agent.position.distance(obs)
		if d < e.params.separation_radius * 2.0 && d > 0 {
			diff := agent.position.sub(obs).normalize().scale(1.0 / d)
			steer = steer.add(diff)
		}
	}
	return steer
}

fn (e &SwarmBehaviorEngine) bounds_force(agent &BoidAgent) Vec3 {
	mut force := Vec3{0, 0, 0}
	margin := 50.0

	if agent.position.x < e.params.bounds_min.x + margin {
		force.x = agent.max_force
	}
	if agent.position.x > e.params.bounds_max.x - margin {
		force.x = -agent.max_force
	}
	if agent.position.y < e.params.bounds_min.y + margin {
		force.y = agent.max_force
	}
	if agent.position.y > e.params.bounds_max.y - margin {
		force.y = -agent.max_force
	}
	if agent.position.z < e.params.bounds_min.z + margin {
		force.z = agent.max_force
	}
	if agent.position.z > e.params.bounds_max.z - margin {
		force.z = -agent.max_force
	}
	return force
}

// ── Step ────────────────────────────────────────────────────────
fn (mut e SwarmBehaviorEngine) step(dt f64) {
	mut forces := []Vec3{len: e.agents.len, init: Vec3{0, 0, 0}}

	for i, agent in e.agents {
		sep := e.separation(&agent).scale(e.params.separation_weight)
		ali := e.alignment(&agent).scale(e.params.alignment_weight)
		coh := e.cohesion(&agent).scale(e.params.cohesion_weight)
		obs := e.obstacle_avoidance(&agent).scale(e.params.avoidance_weight)
		bnd := e.bounds_force(&agent)

		total := sep.add(ali).add(coh).add(obs).add(bnd)

		// Limit force
		if total.length() > agent.max_force {
			forces[i] = total.normalize().scale(agent.max_force)
		} else {
			forces[i] = total
		}
	}

	for i, _ in e.agents {
		e.agents[i].velocity = e.agents[i].velocity.add(forces[i].scale(dt))
		speed := e.agents[i].velocity.length()
		if speed > e.agents[i].max_speed {
			e.agents[i].velocity = e.agents[i].velocity.normalize().scale(e.agents[i].max_speed)
		}
		e.agents[i].position = e.agents[i].position.add(e.agents[i].velocity.scale(dt))
	}
	e.step_count++
}

fn (e &SwarmBehaviorEngine) center_of_mass() Vec3 {
	if e.agents.len == 0 {
		return Vec3{0, 0, 0}
	}
	mut sum := Vec3{0, 0, 0}
	for agent in e.agents {
		sum = sum.add(agent.position)
	}
	return sum.scale(1.0 / f64(e.agents.len))
}

fn (e &SwarmBehaviorEngine) average_speed() f64 {
	if e.agents.len == 0 {
		return 0.0
	}
	mut total := 0.0
	for agent in e.agents {
		total += agent.velocity.length()
	}
	return total / f64(e.agents.len)
}

fn (e &SwarmBehaviorEngine) summary() string {
	com := e.center_of_mass()
	return 'Agents: ${e.agents.len} | Steps: ${e.step_count} | ' +
		'CoM: (${com.x:.1}, ${com.y:.1}, ${com.z:.1}) | ' +
		'AvgSpeed: ${e.average_speed():.2}'
}
