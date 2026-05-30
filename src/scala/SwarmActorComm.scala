// SDACS Swarm Actor Communication — Scala (Phase 551)
// 드론 군집 액터 기반 통신 시스템

package sdacs.actor

import scala.collection.mutable
import java.time.Instant

// 메시지 타입
sealed trait SwarmMessage
case class TelemetryMsg(droneId: String, x: Double, y: Double, z: Double, ts: Long) extends SwarmMessage
case class ConflictAlert(droneA: String, droneB: String, distance: Double) extends SwarmMessage
case class AckMsg(msgId: String, from: String) extends SwarmMessage
case class BroadcastMsg(sender: String, content: String) extends SwarmMessage
case class HeartbeatMsg(droneId: String, battery: Double) extends SwarmMessage

// Actor 인터페이스
trait Actor {
  def id: String
  def receive(msg: SwarmMessage): Unit
  def mailbox: Seq[SwarmMessage]
}

// 드론 Actor (Phase 551)
class DroneActor(val id: String) extends Actor {
  private val inbox = mutable.Queue[SwarmMessage]()
  private var _x = 0.0; private var _y = 0.0; private var _z = 0.0
  private var _battery = 100.0
  private var _msgCount = 0

  def receive(msg: SwarmMessage): Unit = {
    inbox.enqueue(msg)
    _msgCount += 1
    msg match {
      case TelemetryMsg(_, x, y, z, _) =>
        _x = x; _y = y; _z = z
      case HeartbeatMsg(_, batt) =>
        _battery = batt
      case ConflictAlert(_, _, _) =>
        // evasive action would be triggered here
      case _ => ()
    }
  }

  def mailbox: Seq[SwarmMessage] = inbox.toSeq
  def position: (Double, Double, Double) = (_x, _y, _z)
  def battery: Double = _battery
  def messageCount: Int = _msgCount

  def processPending(): Seq[SwarmMessage] = {
    val processed = inbox.toSeq
    inbox.clear()
    processed
  }
}

// 메시지 브로커
class ActorBroker {
  private val actors = mutable.Map[String, DroneActor]()
  private var totalDelivered = 0L

  def register(actor: DroneActor): Unit = actors(actor.id) = actor

  def send(to: String, msg: SwarmMessage): Boolean = {
    actors.get(to) match {
      case Some(actor) =>
        actor.receive(msg)
        totalDelivered += 1
        true
      case None => false
    }
  }

  def broadcast(msg: SwarmMessage, exclude: Set[String] = Set.empty): Int = {
    val targets = actors.filterNot { case (id, _) => exclude.contains(id) }
    targets.values.foreach(_.receive(msg))
    totalDelivered += targets.size
    targets.size
  }

  def actorCount: Int = actors.size
  def totalDelivered: Long = totalDelivered
  def actorIds: Set[String] = actors.keySet.toSet
}

// 토폴로지 기반 라우터
class MeshRouter(broker: ActorBroker) {
  private val edges = mutable.Map[String, mutable.Set[String]]()

  def addLink(a: String, b: String): Unit = {
    edges.getOrElseUpdate(a, mutable.Set.empty).add(b)
    edges.getOrElseUpdate(b, mutable.Set.empty).add(a)
  }

  def neighbors(id: String): Set[String] =
    edges.getOrElse(id, mutable.Set.empty).toSet

  def routeToNeighbors(from: String, msg: SwarmMessage): Int =
    neighbors(from).count(to => broker.send(to, msg))
}
