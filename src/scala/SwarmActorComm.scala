// Phase 551: Swarm Actor Communication — Scala
// SDACS Akka-style actor model for drone swarm message passing

// Phase 551 marker — Actor-based SwarmMessage communication system

package sdacs.actors

import scala.collection.mutable
import java.util.UUID
import java.time.Instant

// ============================================================
// Message types

sealed trait SwarmMessage {
  def messageId: String
  def senderId:  String
  def timestamp: Long
}

case class TelemetryMessage(
  messageId: String = UUID.randomUUID().toString,
  senderId:  String,
  timestamp: Long = Instant.now().toEpochMilli,
  lat:       Double,
  lon:       Double,
  alt:       Double,
  speed:     Double,
  battery:   Double,
  heading:   Double
) extends SwarmMessage

case class CommandMessage(
  messageId: String = UUID.randomUUID().toString,
  senderId:  String,
  timestamp: Long = Instant.now().toEpochMilli,
  targetId:  String,
  command:   String,
  params:    Map[String, String] = Map.empty
) extends SwarmMessage

case class AlertMessage(
  messageId: String = UUID.randomUUID().toString,
  senderId:  String,
  timestamp: Long = Instant.now().toEpochMilli,
  severity:  String,
  message:   String
) extends SwarmMessage

case class ConflictMessage(
  messageId:   String = UUID.randomUUID().toString,
  senderId:    String,
  timestamp:   Long = Instant.now().toEpochMilli,
  otherDrone:  String,
  separationM: Double,
  resolution:  String
) extends SwarmMessage

// ============================================================
// Actor base

trait Actor {
  def actorId: String
  def receive(msg: SwarmMessage): Unit
  def !(msg: SwarmMessage): Unit = receive(msg)
}

// ============================================================
// Drone actor

class DroneActor(val actorId: String) extends Actor {
  private val inbox       = mutable.Queue[SwarmMessage]()
  private var battery     = 100.0
  private var altitude    = 0.0
  private val messageLog  = mutable.ListBuffer[SwarmMessage]()

  def receive(msg: SwarmMessage): Unit = {
    messageLog += msg
    msg match {
      case cmd: CommandMessage if cmd.targetId == actorId =>
        handleCommand(cmd)
      case alert: AlertMessage =>
        println(s"[${actorId}] ALERT from ${alert.senderId}: ${alert.message}")
      case conflict: ConflictMessage if conflict.senderId == actorId =>
        println(s"[${actorId}] Conflict with ${conflict.otherDrone}: ${conflict.resolution}")
      case _: TelemetryMessage => // ignore others' telemetry
      case _ =>
    }
  }

  private def handleCommand(cmd: CommandMessage): Unit = cmd.command match {
    case "TAKEOFF"   => altitude = cmd.params.get("alt").map(_.toDouble).getOrElse(60.0)
      println(s"[$actorId] Taking off to ${altitude}m")
    case "LAND"      => altitude = 0.0; println(s"[$actorId] Landing")
    case "RTL"       => altitude = 0.0; println(s"[$actorId] RTL engaged")
    case "SET_SPEED" => println(s"[$actorId] Speed set to ${cmd.params.getOrElse("speed", "?")}")
    case other       => println(s"[$actorId] Unknown command: $other")
  }

  def currentTelemetry(lat: Double, lon: Double): TelemetryMessage =
    TelemetryMessage(senderId = actorId, lat = lat, lon = lon,
      alt = altitude, speed = 10.0, battery = battery, heading = 0.0)

  def messageCount: Int = messageLog.size
  def getState: Map[String, Any] = Map(
    "id" -> actorId, "battery" -> battery, "altitude" -> altitude,
    "messages" -> messageLog.size
  )
}

// ============================================================
// Swarm message bus (publish-subscribe)

class SwarmMessageBus {
  private val actors      = mutable.Map[String, Actor]()
  private val subscriptions = mutable.Map[String, mutable.Set[String]]()
  private var totalRouted = 0L

  def register(actor: Actor): Unit = actors(actor.actorId) = actor

  def unregister(actorId: String): Unit = actors.remove(actorId)

  def subscribe(actorId: String, topic: String): Unit = {
    subscriptions.getOrElseUpdate(topic, mutable.Set()) += actorId
  }

  def publish(topic: String, msg: SwarmMessage): Int = {
    val subscribers = subscriptions.getOrElse(topic, Set.empty)
    var delivered = 0
    for (id <- subscribers; actor <- actors.get(id)) {
      actor ! msg
      delivered += 1
      totalRouted += 1
    }
    delivered
  }

  def send(targetId: String, msg: SwarmMessage): Boolean = {
    actors.get(targetId).map { a => a ! msg; totalRouted += 1; true }.getOrElse(false)
  }

  def broadcast(msg: SwarmMessage): Int = {
    var count = 0
    for ((_, actor) <- actors if actor.actorId != msg.senderId) {
      actor ! msg
      totalRouted += 1
      count += 1
    }
    count
  }

  def stats: Map[String, Any] = Map(
    "registered" -> actors.size,
    "topics"     -> subscriptions.size,
    "routed"     -> totalRouted
  )
}

// Demo
object SwarmActorDemo extends App {
  val bus = new SwarmMessageBus()
  val drones = (1 to 5).map(i => new DroneActor(s"D00$i"))
  drones.foreach(bus.register)
  drones.foreach(d => bus.subscribe(d.actorId, "alerts"))

  println("Phase 551: Swarm Actor Communication")

  val cmd = CommandMessage(senderId = "GCS", targetId = "D001",
                           command = "TAKEOFF", params = Map("alt" -> "60"))
  bus.send("D001", cmd)

  val alert = AlertMessage(senderId = "D002", severity = "WARNING", message = "Low battery")
  bus.publish("alerts", alert)

  println(s"Bus stats: ${bus.stats}")
}
