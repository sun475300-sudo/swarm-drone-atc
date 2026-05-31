// Phase 551: Swarm Actor Communication Framework
// Actor model for decentralized drone message passing
// SDACS Distributed Communication Module

package sdacs.comm

import scala.collection.mutable
import java.util.UUID
import java.time.Instant

// SwarmMessage types
sealed trait SwarmMessage
case class TelemetryUpdate(droneId: String, position: (Double, Double, Double), timestamp: Long) extends SwarmMessage
case class ConflictAlert(droneId: String, conflictId: String, severity: Double) extends SwarmMessage
case class CommandMessage(targetId: String, command: String, params: Map[String, Any]) extends SwarmMessage
case class AckMessage(messageId: String, droneId: String) extends SwarmMessage
case class HeartbeatMessage(droneId: String, timestamp: Long) extends SwarmMessage

// Actor mailbox for asynchronous Message processing
class ActorMailbox {
  private val messages: mutable.Queue[SwarmMessage] = mutable.Queue.empty
  private var processedCount: Int = 0

  def enqueue(msg: SwarmMessage): Unit = messages.enqueue(msg)
  def dequeue(): Option[SwarmMessage] = if (messages.nonEmpty) Some(messages.dequeue()) else None
  def isEmpty: Boolean = messages.isEmpty
  def size: Int = messages.size
  def incrementProcessed(): Unit = processedCount += 1
  def getProcessedCount: Int = processedCount
}

// Base Actor trait for drone communication
trait Actor {
  val actorId: String
  protected val mailbox: ActorMailbox = new ActorMailbox()

  def receive(msg: SwarmMessage): Unit
  def send(target: Actor, msg: SwarmMessage): Unit = target.mailbox.enqueue(msg)
  def processAll(): Int = {
    var count = 0
    while (!mailbox.isEmpty) {
      mailbox.dequeue().foreach { msg =>
        receive(msg)
        mailbox.incrementProcessed()
        count += 1
      }
    }
    count
  }
}

// Drone actor for swarm communication
class DroneActor(override val actorId: String) extends Actor {
  var lastTelemetry: Option[TelemetryUpdate] = None
  var activeConflicts: mutable.Set[String] = mutable.Set.empty
  var messageLog: mutable.ListBuffer[String] = mutable.ListBuffer.empty

  override def receive(msg: SwarmMessage): Unit = msg match {
    case t: TelemetryUpdate =>
      lastTelemetry = Some(t)
      messageLog.append(s"[TELEMETRY] from ${t.droneId}")
    case c: ConflictAlert =>
      activeConflicts.add(c.conflictId)
      messageLog.append(s"[CONFLICT] severity=${c.severity}")
    case cmd: CommandMessage if cmd.targetId == actorId =>
      messageLog.append(s"[CMD] ${cmd.command}")
    case a: AckMessage =>
      messageLog.append(s"[ACK] ${a.messageId}")
    case h: HeartbeatMessage =>
      messageLog.append(s"[HB] from ${h.droneId}")
    case _ => // ignore
  }

  def getStats: Map[String, Any] = Map(
    "actor_id" -> actorId,
    "messages_processed" -> mailbox.getProcessedCount,
    "active_conflicts" -> activeConflicts.size,
    "log_size" -> messageLog.size
  )
}

// SwarmActorComm: central actor registry and router
class SwarmActorComm(numDrones: Int) {
  private val actors: mutable.Map[String, DroneActor] = mutable.Map.empty
  private var broadcastCount: Int = 0

  // Initialize drone actors
  (0 until numDrones).foreach { i =>
    val id = s"drone_$i"
    actors(id) = new DroneActor(id)
  }

  def getActor(droneId: String): Option[DroneActor] = actors.get(droneId)

  def broadcast(msg: SwarmMessage, excludeId: String = ""): Int = {
    var count = 0
    actors.values.filter(_.actorId != excludeId).foreach { actor =>
      actor.mailbox.enqueue(msg)
      count += 1
    }
    broadcastCount += 1
    count
  }

  def routeMessage(fromId: String, toId: String, msg: SwarmMessage): Boolean = {
    (actors.get(fromId), actors.get(toId)) match {
      case (Some(from), Some(to)) =>
        from.send(to, msg)
        true
      case _ => false
    }
  }

  def processAllActors(): Map[String, Int] = {
    actors.map { case (id, actor) => id -> actor.processAll() }.toMap
  }

  def getSystemStats: Map[String, Any] = Map(
    "total_actors" -> actors.size,
    "broadcast_count" -> broadcastCount,
    "message_model" -> "Actor"
  )
}

object Main extends App {
  println("SDACS Swarm Actor Communication v551")
  val comm = new SwarmActorComm(5)

  val telemetry = TelemetryUpdate("drone_0", (10.0, 20.0, 100.0), Instant.now().toEpochMilli)
  comm.broadcast(telemetry)

  val processedCounts = comm.processAllActors()
  println(s"Processed: $processedCounts")
  println(s"SwarmMessage routing active")
  println(s"System: ${comm.getSystemStats}")
}
