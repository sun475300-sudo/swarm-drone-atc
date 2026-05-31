// SwarmActorComm.scala - Actor-based communication for SDACS (Phase 551)
// Akka actor model for drone swarm message passing

package sdacs.actor

import akka.actor.{Actor, ActorRef, ActorSystem, Props, Terminated}
import akka.pattern.ask
import scala.concurrent.duration._

// SwarmMessage types for drone communication
sealed trait SwarmMessage
case class TelemetryMessage(droneId: String, x: Double, y: Double, z: Double, battery: Int) extends SwarmMessage
case class ConflictMessage(droneA: String, droneB: String, distance: Double) extends SwarmMessage
case class CommandMessage(target: String, command: String, params: Map[String, String]) extends SwarmMessage
case class HeartbeatMessage(droneId: String, seqNum: Int) extends SwarmMessage
case class RegisterMessage(droneId: String, ref: ActorRef) extends SwarmMessage
case object GetStatusMessage extends SwarmMessage

// Drone Actor: handles telemetry and commands
class DroneActor(droneId: String) extends Actor {
  var position = (0.0, 0.0, 50.0)
  var battery  = 100
  var messageCount = 0

  override def receive: Receive = {
    case TelemetryMessage(id, x, y, z, bat) if id == droneId =>
      position = (x, y, z)
      battery  = bat
      messageCount += 1
      sender() ! s"ACK:$id:$messageCount"

    case CommandMessage(target, cmd, _) if target == droneId =>
      messageCount += 1
      sender() ! s"CMD_OK:$cmd"

    case HeartbeatMessage(id, seq) if id == droneId =>
      sender() ! s"HB_ACK:$seq"

    case GetStatusMessage =>
      sender() ! Map(
        "id"       -> droneId,
        "position" -> position.toString,
        "battery"  -> battery.toString,
        "msgs"     -> messageCount.toString
      )
  }
}

// Swarm Coordinator Actor: manages all drone actors
class SwarmCoordinatorActor extends Actor {
  var drones: Map[String, ActorRef] = Map.empty
  var conflictCount = 0

  override def receive: Receive = {
    case RegisterMessage(droneId, ref) =>
      drones = drones + (droneId -> ref)
      context.watch(ref)
      sender() ! s"REGISTERED:$droneId"

    case msg: TelemetryMessage =>
      drones.get(msg.droneId).foreach(_ ! msg)

    case msg: ConflictMessage =>
      conflictCount += 1
      sender() ! s"CONFLICT_LOGGED:${msg.droneA}-${msg.droneB}"

    case msg: CommandMessage =>
      drones.get(msg.target).foreach(_ forward msg)

    case Terminated(ref) =>
      drones = drones.filter { case (_, r) => r != ref }

    case GetStatusMessage =>
      sender() ! Map(
        "drones"    -> drones.size.toString,
        "conflicts" -> conflictCount.toString
      )
  }
}

object SwarmActorComm {
  def createSystem(name: String = "sdacs-swarm"): ActorSystem =
    ActorSystem(name)

  def createCoordinator(system: ActorSystem): ActorRef =
    system.actorOf(Props[SwarmCoordinatorActor], "coordinator")

  def createDroneActor(system: ActorSystem, droneId: String): ActorRef =
    system.actorOf(Props(new DroneActor(droneId)), s"drone-$droneId")
}
