// Phase 551: Scala Actor-Based Swarm Communication
// Akka-style Actor 모델로 군집 드론 간 비동기 메시지 통신 시뮬레이션

import scala.collection.mutable

sealed trait SwarmMessage
case class Position(droneId: String, x: Double, y: Double, z: Double) extends SwarmMessage
case class Command(from: String, to: String, action: String) extends SwarmMessage
case class Heartbeat(droneId: String, timestamp: Long) extends SwarmMessage
case class Alert(droneId: String, level: Int, message: String) extends SwarmMessage

class PRNG(seed: Long) {
  private var state: Long = seed ^ 0x6c62272e07bb0142L
  def next(): Long = { state ^= (state << 13); state ^= (state >> 7); state ^= (state << 17); state }
  def uniform(): Double = (next().abs % 10000).toDouble / 10000.0
  def normal(): Double = { val u1 = math.max(uniform(), 1e-10); val u2 = uniform(); math.sqrt(-2*math.log(u1)) * math.cos(2*math.Pi*u2) }
}

class DroneActor(val droneId: String, rng: PRNG) {
  val inbox: mutable.Queue[SwarmMessage] = mutable.Queue()
  var position: (Double, Double, Double) = (rng.normal() * 50, rng.normal() * 50, 50 + rng.uniform() * 50)
  var messagesProcessed: Int = 0
  var alertsSent: Int = 0

  def receive(msg: SwarmMessage): Unit = inbox.enqueue(msg)

  def process(): List[SwarmMessage] = {
    val responses = mutable.ListBuffer[SwarmMessage]()
    while (inbox.nonEmpty) {
      inbox.dequeue() match {
        case Position(id, x, y, z) =>
          val dist = math.sqrt(math.pow(position._1 - x, 2) + math.pow(position._2 - y, 2) + math.pow(position._3 - z, 2))
          if (dist < 20) responses += Alert(droneId, 1, s"Proximity alert: $id at ${dist.formatted("%.1f")}m")
        case Command(_, _, action) =>
          if (action == "report") responses += Position(droneId, position._1, position._2, position._3)
        case Heartbeat(id, ts) => // acknowledged
        case Alert(id, level, _) =>
          if (level >= 2) { alertsSent += 1; responses += Command(droneId, id, "evade") }
      }
      messagesProcessed += 1
    }
    responses.toList
  }

  def move(dt: Double): Unit = {
    position = (position._1 + rng.normal() * dt, position._2 + rng.normal() * dt, position._3 + rng.normal() * 0.1 * dt)
  }
}

class SwarmCommunicationSystem(nDrones: Int, seed: Long = 42L) {
  val rng = new PRNG(seed)
  val actors: Array[DroneActor] = Array.tabulate(nDrones)(i => new DroneActor(s"drone_$i", new PRNG(seed + i)))
  var totalMessages: Int = 0
  var totalAlerts: Int = 0

  def broadcast(msg: SwarmMessage): Unit = actors.foreach(_.receive(msg))

  def step(): Unit = {
    // Move all drones
    actors.foreach(_.move(1.0))
    // Broadcast positions
    actors.foreach { a =>
      val pos = a.position
      broadcast(Position(a.droneId, pos._1, pos._2, pos._3))
    }
    // Process messages
    val responses = actors.flatMap(_.process())
    totalMessages += actors.map(_.messagesProcessed).sum
    totalAlerts += responses.count(_.isInstanceOf[Alert])
    // Deliver responses
    responses.foreach {
      case cmd: Command => actors.find(_.droneId == cmd.to).foreach(_.receive(cmd))
      case _ =>
    }
  }

  def run(steps: Int): Unit = (0 until steps).foreach(_ => step())
}

object SwarmActorComm extends App {
  val system = new SwarmCommunicationSystem(10, 42L)
  system.run(20)
  println(s"Drones: ${system.actors.length}")
  println(s"Total messages processed: ${system.totalMessages}")
  println(s"Total alerts: ${system.totalAlerts}")
}
