// Phase 551: Swarm Actor Communication — 군집 드론 액터 모델 통신 (Scala)
// Akka-style actor model for swarm drone inter-drone messaging.
package sdacs.comm

import scala.collection.mutable
import scala.util.{Try, Success, Failure}

object PHASE { val value = 551 }

// ── Message types ──────────────────────────────────────────────────

sealed trait SwarmMessage
case class HeartbeatMsg(droneId: Int, battery: Double, ts: Long)     extends SwarmMessage
case class TelemetryMsg(droneId: Int, x: Double, y: Double, z: Double) extends SwarmMessage
case class CommandMsg(targetId: Int, cmd: String, params: Map[String, Any]) extends SwarmMessage
case class AlertMsg(droneId: Int, severity: String, detail: String)   extends SwarmMessage
case class AckMsg(seqId: Int, success: Boolean)                       extends SwarmMessage

// ── Actor trait ────────────────────────────────────────────────────

trait Actor {
  val id: String
  protected val mailbox: mutable.Queue[SwarmMessage] = mutable.Queue.empty
  var messageCount: Int = 0

  def receive(msg: SwarmMessage): Unit

  def send(msg: SwarmMessage): Unit = {
    mailbox.enqueue(msg)
  }

  def process(): Unit = {
    while (mailbox.nonEmpty) {
      val msg = mailbox.dequeue()
      messageCount += 1
      receive(msg)
    }
  }
}

// ── Drone actor ────────────────────────────────────────────────────

class DroneActor(val droneId: Int, val supervisor: SupervisorActor)
    extends Actor {

  val id: String = s"drone-$droneId"
  var x: Double = droneId * 50.0
  var y: Double = 0.0
  var z: Double = 50.0
  var battery: Double = 100.0
  var status: String = "idle"
  val eventLog: mutable.ArrayBuffer[String] = mutable.ArrayBuffer.empty

  override def receive(msg: SwarmMessage): Unit = msg match {
    case HeartbeatMsg(_, bat, _) =>
      battery = bat
      supervisor.send(AckMsg(messageCount, success = true))

    case TelemetryMsg(_, px, py, pz) =>
      x = px; y = py; z = pz
      eventLog += s"TM: ($px,$py,$pz)"

    case CommandMsg(_, cmd, _) =>
      status = cmd
      eventLog += s"CMD: $cmd"

    case AlertMsg(_, sev, detail) =>
      eventLog += s"ALERT[$sev]: $detail"

    case AckMsg(seq, ok) =>
      eventLog += s"ACK seq=$seq ok=$ok"
  }

  def summary: Map[String, Any] = Map(
    "droneId"      -> droneId,
    "battery"      -> battery,
    "status"       -> status,
    "messages"     -> messageCount,
    "eventLogSize" -> eventLog.size
  )
}

// ── Supervisor actor ───────────────────────────────────────────────

class SupervisorActor extends Actor {
  val id: String = "supervisor"
  val drones: mutable.Map[Int, DroneActor] = mutable.Map.empty
  var conflicts: Int = 0
  var healed: Int = 0

  def spawnDrone(droneId: Int): DroneActor = {
    val d = new DroneActor(droneId, this)
    drones(droneId) = d
    d
  }

  override def receive(msg: SwarmMessage): Unit = msg match {
    case AckMsg(_, true)  => healed += 1
    case AckMsg(_, false) => conflicts += 1
    case AlertMsg(did, "CRITICAL", _) =>
      drones.get(did).foreach(_.send(CommandMsg(did, "return_home", Map.empty)))
    case _ => ()
  }

  def broadcastTelemetry(): Unit = {
    drones.foreach { case (_, drone) =>
      drone.send(HeartbeatMsg(drone.droneId, drone.battery, System.currentTimeMillis()))
    }
  }

  def runAll(): Unit = {
    process()
    drones.values.foreach(_.process())
  }

  def fleetSummary: Map[String, Any] = Map(
    "phase"     -> PHASE.value,
    "drones"    -> drones.size,
    "healed"    -> healed,
    "conflicts" -> conflicts
  )
}

// ── Entry point ────────────────────────────────────────────────────

object SwarmActorComm extends App {
  println(s"Phase ${PHASE.value}: SwarmActorComm — 군집 드론 액터 통신 모델")
  val supervisor = new SupervisorActor
  (0 until 5).foreach(supervisor.spawnDrone)
  supervisor.broadcastTelemetry()
  supervisor.runAll()
  val s = supervisor.fleetSummary
  println(s"Drones: ${s("drones")}, Healed: ${s("healed")}")
}
