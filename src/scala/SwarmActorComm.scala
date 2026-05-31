// Phase 551 — Akka Actor-based swarm communication
// SwarmMessage types, Actor receive logic for drone coordination

package swarm.atc.comm

import akka.actor.{Actor, ActorRef, ActorSystem, Props, Terminated}
import akka.event.Logging
import scala.collection.mutable

// ── SwarmMessage ADT ────────────────────────────────────────────────────────

sealed trait SwarmMessage

case class DroneRegister(droneId: String, actorRef: ActorRef)   extends SwarmMessage
case class DroneDeregister(droneId: String)                      extends SwarmMessage
case class TelemetryUpdate(droneId: String,
                            x: Double, y: Double, z: Double,
                            velocityX: Double, velocityY: Double, velocityZ: Double,
                            timestamp: Long)                      extends SwarmMessage
case class ConflictAlert(droneA: String, droneB: String,
                          separationM: Double)                    extends SwarmMessage
case class ResolutionCommand(droneId: String,
                              newHeadingDeg: Double,
                              newAltM: Double)                    extends SwarmMessage
case class MissionAssign(droneId: String, waypointIds: List[Int]) extends SwarmMessage
case class SwarmStatusRequest(requesterId: String)               extends SwarmMessage
case class SwarmStatusResponse(droneCount: Int,
                                activeConflicts: Int,
                                snapshot: Map[String, TelemetryUpdate]) extends SwarmMessage
case object Heartbeat                                             extends SwarmMessage
case object ShutdownSwarm                                         extends SwarmMessage

// ── SwarmCoordinator Actor ───────────────────────────────────────────────────

/**
 * Central coordinator actor.  Drones register, send telemetry, and receive
 * resolution commands through this actor.  Phase 551 stub — routing logic only.
 */
class SwarmCoordinatorActor extends Actor {
  private val log           = Logging(context.system, this)
  private val registry      = mutable.Map.empty[String, ActorRef]
  private val latestTelemetry = mutable.Map.empty[String, TelemetryUpdate]
  private var conflictCount = 0

  override def receive: Receive = {

    case DroneRegister(id, ref) =>
      registry(id) = ref
      context.watch(ref)
      log.info(s"[551] Drone registered: $id  total=${registry.size}")

    case DroneDeregister(id) =>
      registry.remove(id)
      latestTelemetry.remove(id)
      log.info(s"[551] Drone deregistered: $id")

    case t: TelemetryUpdate =>
      latestTelemetry(t.droneId) = t
      checkProximityConflicts(t)

    case ConflictAlert(a, b, sep) =>
      conflictCount += 1
      log.warning(s"[551] Conflict detected: $a <-> $b  sep=${sep}m")
      resolveConflict(a, b, sep)

    case cmd: ResolutionCommand =>
      registry.get(cmd.droneId).foreach(_ ! cmd)

    case MissionAssign(id, wps) =>
      registry.get(id).foreach(_ ! MissionAssign(id, wps))
      log.info(s"[551] Mission assigned to $id: waypoints=${wps.mkString(",")}")

    case SwarmStatusRequest(reqId) =>
      sender() ! SwarmStatusResponse(
        droneCount      = registry.size,
        activeConflicts = conflictCount,
        snapshot        = latestTelemetry.toMap
      )

    case Heartbeat =>
      log.debug(s"[551] Heartbeat — drones=${registry.size}")

    case Terminated(ref) =>
      registry.find(_._2 == ref).foreach { case (id, _) =>
        registry.remove(id)
        log.warning(s"[551] Actor terminated unexpectedly: $id")
      }

    case ShutdownSwarm =>
      log.info("[551] Swarm shutdown initiated.")
      context.stop(self)
  }

  // ── private helpers ────────────────────────────────────────────────────────

  private def checkProximityConflicts(t: TelemetryUpdate): Unit = {
    val SEPARATION_THRESHOLD_M = 5.0
    latestTelemetry.foreach { case (otherId, other) =>
      if (otherId != t.droneId) {
        val dx = t.x - other.x
        val dy = t.y - other.y
        val dz = t.z - other.z
        val dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        if (dist < SEPARATION_THRESHOLD_M)
          self ! ConflictAlert(t.droneId, otherId, dist)
      }
    }
  }

  private def resolveConflict(a: String, b: String, sepM: Double): Unit = {
    // Stub: assign altitude separation — even droneId climbs, odd descends
    val newAltA = latestTelemetry.get(a).map(_.z + 2.0).getOrElse(10.0)
    val newAltB = latestTelemetry.get(b).map(_.z - 2.0).getOrElse(8.0)
    self ! ResolutionCommand(a, 0.0, newAltA)
    self ! ResolutionCommand(b, 0.0, newAltB)
  }
}

// ── DroneActor stub ──────────────────────────────────────────────────────────

class DroneActor(droneId: String, coordinator: ActorRef) extends Actor {
  private val log = Logging(context.system, this)

  override def preStart(): Unit = {
    coordinator ! DroneRegister(droneId, self)
  }

  override def receive: Receive = {
    case cmd: ResolutionCommand =>
      log.info(s"[551] $droneId executing resolution: alt=${cmd.newAltM}m heading=${cmd.newHeadingDeg}°")

    case MissionAssign(_, wps) =>
      log.info(s"[551] $droneId received mission with ${wps.size} waypoints")

    case msg: SwarmMessage =>
      log.debug(s"[551] $droneId unhandled SwarmMessage: $msg")
  }
}

// ── Entry point (demo) ───────────────────────────────────────────────────────

object SwarmActorCommMain extends App {
  val system      = ActorSystem("SwarmATC-551")
  val coordinator = system.actorOf(Props[SwarmCoordinatorActor], "coordinator")

  val drone1 = system.actorOf(Props(new DroneActor("D001", coordinator)), "drone-001")
  val drone2 = system.actorOf(Props(new DroneActor("D002", coordinator)), "drone-002")

  coordinator ! TelemetryUpdate("D001", 10.0, 10.0, 20.0, 0.5, 0.0, 0.0, System.currentTimeMillis())
  coordinator ! TelemetryUpdate("D002", 10.2, 10.1, 20.0, -0.5, 0.0, 0.0, System.currentTimeMillis())
  coordinator ! Heartbeat

  Thread.sleep(500)
  system.terminate()
}
