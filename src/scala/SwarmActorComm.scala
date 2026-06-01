// Phase 551 — Swarm Actor Communication Module
// Scala module for actor-based message passing in a drone swarm system.

package swarm.comm

import scala.collection.mutable

// ===== Message Types =====

/** Base trait for all swarm messages */
sealed trait SwarmMessage {
  def senderId: String
  def recipientId: String
  def timestamp: Long
}

/** Telemetry message from a drone to the controller */
case class TelemetryMessage(
    senderId: String,
    recipientId: String,
    timestamp: Long,
    x: Double,
    y: Double,
    z: Double,
    battery: Double,
    speed: Double
) extends SwarmMessage

/** Command message from controller to a drone */
case class CommandMessage(
    senderId: String,
    recipientId: String,
    timestamp: Long,
    commandType: String,
    params: Map[String, Double]
) extends SwarmMessage

/** Alert message broadcast across the swarm */
case class AlertMessage(
    senderId: String,
    recipientId: String,
    timestamp: Long,
    alertCode: String,
    severity: Int,
    description: String
) extends SwarmMessage

/** Acknowledgment message */
case class AckMessage(
    senderId: String,
    recipientId: String,
    timestamp: Long,
    originalMessageId: String,
    success: Boolean
) extends SwarmMessage

// ===== Actor Interface =====

/** Base Actor trait for all swarm nodes */
trait Actor {
  def actorId: String
  def mailbox: mutable.Queue[SwarmMessage]
  def receive(msg: SwarmMessage): Unit
  def send(msg: SwarmMessage, target: Actor): Unit = target.receive(msg)
  def processAll(): Unit = while (mailbox.nonEmpty) receive(mailbox.dequeue())
}

// ===== Drone Actor =====

/** DroneActor handles communication for a single drone node */
class DroneActor(val actorId: String, var battery: Double = 100.0) extends Actor {
  val mailbox: mutable.Queue[SwarmMessage] = mutable.Queue.empty
  var position: (Double, Double, Double) = (0.0, 0.0, 50.0)
  var messageHistory: List[SwarmMessage] = Nil

  override def receive(msg: SwarmMessage): Unit = {
    mailbox.enqueue(msg)
    messageHistory = msg :: messageHistory
  }

  override def processAll(): Unit = {
    while (mailbox.nonEmpty) {
      mailbox.dequeue() match {
        case cmd: CommandMessage =>
          handleCommand(cmd)
        case alert: AlertMessage =>
          println(s"[$actorId] ALERT[${alert.severity}]: ${alert.description}")
        case _: TelemetryMessage => // drone ignores own telemetry echoes
        case ack: AckMessage =>
          println(s"[$actorId] ACK received for ${ack.originalMessageId}")
        case _ =>
      }
    }
  }

  private def handleCommand(cmd: CommandMessage): Unit = {
    cmd.commandType match {
      case "MOVE" =>
        position = (
          cmd.params.getOrElse("x", position._1),
          cmd.params.getOrElse("y", position._2),
          cmd.params.getOrElse("z", position._3)
        )
        println(s"[$actorId] Moving to ${position}")
      case "RTL" => println(s"[$actorId] Returning to launch")
      case "HOLD" => println(s"[$actorId] Holding position")
      case other => println(s"[$actorId] Unknown command: $other")
    }
  }

  def createTelemetry(recipientId: String): TelemetryMessage = {
    TelemetryMessage(actorId, recipientId, System.currentTimeMillis(),
      position._1, position._2, position._3, battery, 5.0)
  }
}

// ===== Controller Actor =====

/** ControllerActor manages the drone swarm and routes messages */
class ControllerActor(val actorId: String = "GCS") extends Actor {
  val mailbox: mutable.Queue[SwarmMessage] = mutable.Queue.empty
  val registeredDrones: mutable.Map[String, DroneActor] = mutable.Map.empty
  var telemetryLog: List[TelemetryMessage] = Nil

  def registerDrone(drone: DroneActor): Unit = {
    registeredDrones(drone.actorId) = drone
    println(s"[$actorId] Registered drone: ${drone.actorId}")
  }

  override def receive(msg: SwarmMessage): Unit = {
    mailbox.enqueue(msg)
  }

  override def processAll(): Unit = {
    while (mailbox.nonEmpty) {
      mailbox.dequeue() match {
        case tel: TelemetryMessage =>
          telemetryLog = tel :: telemetryLog
          println(s"[$actorId] Telemetry from ${tel.senderId}: pos=(${tel.x},${tel.y},${tel.z})")
        case alert: AlertMessage =>
          println(s"[$actorId] Swarm alert: ${alert.alertCode} from ${alert.senderId}")
          broadcastAlert(alert.copy(senderId = actorId))
        case _ =>
      }
    }
  }

  def broadcastAlert(alert: AlertMessage): Unit = {
    registeredDrones.values.foreach(drone =>
      drone.receive(alert.copy(recipientId = drone.actorId))
    )
  }

  def sendCommand(droneId: String, cmdType: String, params: Map[String, Double]): Boolean = {
    registeredDrones.get(droneId) match {
      case Some(drone) =>
        val cmd = CommandMessage(actorId, droneId, System.currentTimeMillis(), cmdType, params)
        drone.receive(cmd)
        true
      case None => false
    }
  }

  def summary(): Map[String, Any] = Map(
    "registered_drones" -> registeredDrones.size,
    "telemetry_received" -> telemetryLog.size,
    "phase" -> "551"
  )
}

// ===== Main =====
object SwarmActorComm extends App {
  println("Phase 551: Swarm Actor Communication System")

  val controller = new ControllerActor("GCS-1")
  val drones = (1 to 4).map(i => new DroneActor(s"D00$i", 100.0 - i * 5.0))
  drones.foreach(controller.registerDrone)

  // Drones send telemetry
  drones.foreach { d =>
    controller.receive(d.createTelemetry("GCS-1"))
  }
  controller.processAll()

  // Controller sends commands
  controller.sendCommand("D001", "MOVE", Map("x" -> 10.0, "y" -> 5.0, "z" -> 55.0))
  drones.head.processAll()

  println(s"Summary: ${controller.summary()}")
}
