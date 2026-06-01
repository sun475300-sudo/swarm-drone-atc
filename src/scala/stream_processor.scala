// Phase 632 — Scala Stream Processor for Drone Telemetry
// Functional stream processing pipeline for real-time telemetry data

package sdacs.stream

import scala.collection.mutable

case class TelemetryEvent(droneId: String, timestamp: Double, position: (Double, Double, Double))
case class ConflictAlert(drone1: String, drone2: String, distance: Double)

object StreamProcessor {
  def process(events: LazyList[TelemetryEvent], minSeparation: Double = 50.0): LazyList[ConflictAlert] = {
    val buffer = mutable.Map.empty[String, TelemetryEvent]
    events.flatMap { event =>
      buffer.update(event.droneId, event)
      buffer.values.toSeq
        .filter(_.droneId != event.droneId)
        .flatMap { other =>
          val dist = euclidean(event.position, other.position)
          if (dist < minSeparation) Some(ConflictAlert(event.droneId, other.droneId, dist))
          else None
        }
        .to(LazyList)
    }
  }

  private def euclidean(a: (Double, Double, Double), b: (Double, Double, Double)): Double =
    math.sqrt(math.pow(a._1 - b._1, 2) + math.pow(a._2 - b._2, 2) + math.pow(a._3 - b._3, 2))
}
