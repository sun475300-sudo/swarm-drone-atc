// stream_processor.scala - Akka Streams processor for SDACS telemetry
package sdacs.stream

import akka.actor.ActorSystem
import akka.stream._
import akka.stream.scaladsl._

case class DroneFrame(droneId: String, ts: Long, x: Double, y: Double, z: Double, battery: Int)
case class ConflictAlert(droneA: String, droneB: String, dist: Double)

object StreamProcessor {
  def filterLowBattery(threshold: Int): Flow[DroneFrame, DroneFrame, _] =
    Flow[DroneFrame].filter(_.battery >= threshold)

  def computeSpeed: Flow[DroneFrame, (DroneFrame, Double), _] =
    Flow[DroneFrame].map(f => (f, Math.sqrt(f.x * f.x + f.y * f.y)))

  def buildPipeline(source: Source[DroneFrame, _]): Source[DroneFrame, _] =
    source.via(filterLowBattery(15))
}
