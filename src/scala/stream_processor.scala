// Phase 632 — Swarm Telemetry Stream Processor in Scala
package sdacs.stream

import akka.stream.scaladsl._
import akka.actor.ActorSystem

case class TelemetryFrame(droneId: String, x: Double, y: Double, z: Double, ts: Long)
case class ConflictAlert(drone1: String, drone2: String, distance: Double, ts: Long)

object StreamProcessor {
  def conflictDetectionFlow(minSep: Double): Flow[TelemetryFrame, ConflictAlert, _] =
    Flow[TelemetryFrame]
      .groupedWithin(100, scala.concurrent.duration.DurationInt(1).second)
      .mapConcat { frames =>
        for {
          a <- frames; b <- frames if a.droneId < b.droneId
          d = math.sqrt(math.pow(a.x-b.x,2)+math.pow(a.y-b.y,2)+math.pow(a.z-b.z,2))
          if d < minSep
        } yield ConflictAlert(a.droneId, b.droneId, d, System.currentTimeMillis())
      }
}
