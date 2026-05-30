// Phase 551: SwarmActorComm — Akka Actor 기반 군집 드론 통신
// SDACS Swarm Actor Communication Module

import akka.actor.{Actor, ActorRef, ActorSystem, Props}
import scala.concurrent.duration._
import scala.collection.mutable

// 스웜 메시지 타입 정의
sealed trait SwarmMessage
case class DroneStatus(droneId: Int, lat: Double, lon: Double, alt: Double, battery: Double) extends SwarmMessage
case class FlightCommand(droneId: Int, command: String, params: Map[String, Double]) extends SwarmMessage
case class ConflictAlert(droneId1: Int, droneId2: Int, separation: Double) extends SwarmMessage
case class HeartbeatMessage(droneId: Int, timestamp: Long) extends SwarmMessage
case class AckMessage(droneId: Int, messageId: String) extends SwarmMessage
case object GetStatus extends SwarmMessage
case object Shutdown extends SwarmMessage

// 드론 에이전트 Actor
class DroneActor(droneId: Int, controller: ActorRef) extends Actor {
  private var position = (0.0, 0.0, 0.0)
  private var battery = 100.0
  private var isArmed = false

  def receive: Receive = {
    case FlightCommand(id, cmd, params) if id == droneId =>
      handleCommand(cmd, params)
      controller ! AckMessage(droneId, s"cmd_${System.currentTimeMillis()}")

    case HeartbeatMessage(id, ts) if id == droneId =>
      controller ! DroneStatus(droneId, position._1, position._2, position._3, battery)

    case ConflictAlert(id1, id2, sep) =>
      if (id1 == droneId || id2 == droneId) {
        println(s"[Drone $droneId] CONFLICT ALERT: separation=${sep}m with drone ${if (id1 == droneId) id2 else id1}")
        executeEmergencyAvoidance()
      }

    case GetStatus =>
      sender() ! DroneStatus(droneId, position._1, position._2, position._3, battery)

    case Shutdown =>
      context.stop(self)
  }

  private def handleCommand(cmd: String, params: Map[String, Double]): Unit = cmd match {
    case "TAKEOFF" =>
      isArmed = true
      position = (position._1, position._2, params.getOrElse("alt", 30.0))
      println(s"[Drone $droneId] TAKEOFF to alt=${position._3}m")

    case "LAND" =>
      position = (position._1, position._2, 0.0)
      isArmed = false
      println(s"[Drone $droneId] LANDED")

    case "GOTO" =>
      val lat = params.getOrElse("lat", position._1)
      val lon = params.getOrElse("lon", position._2)
      val alt = params.getOrElse("alt", position._3)
      position = (lat, lon, alt)
      println(s"[Drone $droneId] GOTO lat=$lat lon=$lon alt=$alt")

    case "RTL" =>
      position = (0.0, 0.0, 0.0)
      isArmed = false
      println(s"[Drone $droneId] Return to Launch")

    case _ =>
      println(s"[Drone $droneId] Unknown command: $cmd")
  }

  private def executeEmergencyAvoidance(): Unit = {
    val avoidAlt = position._3 + 10.0
    position = (position._1, position._2, avoidAlt)
    println(s"[Drone $droneId] Emergency avoidance: climbing to ${avoidAlt}m")
  }
}

// 스웜 컨트롤러 Actor
class SwarmController(droneCount: Int) extends Actor {
  private val drones = mutable.Map.empty[Int, ActorRef]
  private val statuses = mutable.Map.empty[Int, DroneStatus]
  private var conflictCount = 0

  override def preStart(): Unit = {
    (0 until droneCount).foreach { id =>
      val drone = context.actorOf(Props(new DroneActor(id, self)), s"drone-$id")
      drones(id) = drone
    }
    println(s"SwarmController: $droneCount drones initialized")
  }

  def receive: Receive = {
    case status: DroneStatus =>
      statuses(status.droneId) = status
      checkForConflicts(status)

    case cmd: FlightCommand =>
      drones.get(cmd.droneId).foreach(_ ! cmd)

    case GetStatus =>
      sender() ! statuses.values.toList

    case Shutdown =>
      drones.values.foreach(_ ! Shutdown)
      context.stop(self)
  }

  private def checkForConflicts(updated: DroneStatus): Unit = {
    val minSeparation = 5.0
    statuses.values
      .filter(_.droneId != updated.droneId)
      .foreach { other =>
        val sep = math.sqrt(
          math.pow(updated.lat - other.lat, 2) +
          math.pow(updated.lon - other.lon, 2) +
          math.pow(updated.alt - other.alt, 2)
        )
        if (sep < minSeparation) {
          conflictCount += 1
          val alert = ConflictAlert(updated.droneId, other.droneId, sep)
          drones.values.foreach(_ ! alert)
        }
      }
  }
}

object SwarmActorComm extends App {
  val system = ActorSystem("SDACSwarm")
  val controller = system.actorOf(Props(new SwarmController(10)), "swarm-controller")
  println("SDACS Swarm Actor Communication System started — Phase 551")
  Thread.sleep(1000)
  system.terminate()
}
