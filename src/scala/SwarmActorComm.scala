// P551: SwarmActorComm - Scala Actor-based drone swarm communication
// Phase 551: Akka Actor messaging for distributed swarm coordination

package com.sdacs.swarm.comm

import akka.actor.{Actor, ActorRef, ActorSystem, Props}
import akka.pattern.ask
import akka.util.Timeout
import scala.concurrent.duration._
import scala.concurrent.{ExecutionContext, Future}

// Messages for inter-drone communication
sealed trait SwarmMessage
case class DroneRegistered(droneId: String)           extends SwarmMessage
case class DroneLeft(droneId: String)                 extends SwarmMessage
case class TelemetryUpdate(droneId: String, pos: (Double,Double,Double), bat: Double) extends SwarmMessage
case class ConflictAlert(droneA: String, droneB: String, distance: Double) extends SwarmMessage
case class CommandMessage(droneId: String, command: String, params: Map[String,Any]) extends SwarmMessage
case class AckMessage(messageId: String, success: Boolean)   extends SwarmMessage
case object GetSwarmState extends SwarmMessage
case class SwarmState(drones: Map[String, (Double,Double,Double)]) extends SwarmMessage

class SwarmCoordinatorActor extends Actor {
  private var registeredDrones: Map[String, ActorRef] = Map.empty
  private var dronePositions: Map[String, (Double,Double,Double)] = Map.empty

  override def receive: Receive = {
    case DroneRegistered(droneId) =>
      registeredDrones = registeredDrones + (droneId -> sender())
      dronePositions = dronePositions + (droneId -> (0.0, 0.0, 60.0))
      sender() ! AckMessage(droneId, success = true)

    case DroneLeft(droneId) =>
      registeredDrones = registeredDrones - droneId
      dronePositions = dronePositions - droneId

    case TelemetryUpdate(droneId, pos, _) =>
      dronePositions = dronePositions + (droneId -> pos)

    case ConflictAlert(droneA, droneB, distance) =>
      registeredDrones.get(droneA).foreach(_ ! CommandMessage(droneA, "HOLD", Map("reason" -> "conflict")))
      registeredDrones.get(droneB).foreach(_ ! CommandMessage(droneB, "HOLD", Map("reason" -> "conflict")))

    case GetSwarmState =>
      sender() ! SwarmState(dronePositions)
  }
}

class DroneActor(droneId: String, coordinator: ActorRef) extends Actor {
  private var position: (Double, Double, Double) = (0.0, 0.0, 60.0)
  private var battery: Double = 100.0

  override def preStart(): Unit = {
    coordinator ! DroneRegistered(droneId)
  }

  override def postStop(): Unit = {
    coordinator ! DroneLeft(droneId)
  }

  override def receive: Receive = {
    case CommandMessage(_, cmd, params) =>
      cmd match {
        case "MOVE_TO" =>
          val x = params.getOrElse("x", 0.0).asInstanceOf[Double]
          val y = params.getOrElse("y", 0.0).asInstanceOf[Double]
          val z = params.getOrElse("z", 60.0).asInstanceOf[Double]
          position = (x, y, z)
          coordinator ! TelemetryUpdate(droneId, position, battery)
        case "HOLD" =>
          // Maintain current position
        case _ =>
      }
      sender() ! AckMessage(droneId, success = true)

    case TelemetryUpdate(id, pos, bat) if id == droneId =>
      position = pos
      battery = bat
  }
}

object SwarmActorComm {
  def createSystem(systemName: String = "sdacs-swarm"): ActorSystem = {
    ActorSystem(systemName)
  }

  def createCoordinator(system: ActorSystem): ActorRef = {
    system.actorOf(Props[SwarmCoordinatorActor](), "coordinator")
  }

  def createDrone(system: ActorSystem, droneId: String, coordinator: ActorRef): ActorRef = {
    system.actorOf(Props(new DroneActor(droneId, coordinator)), s"drone-$droneId")
  }
}
