// Stream Processor — Scala stub for SDACS telemetry pipeline
package sdacs.streaming

case class TelemetryFrame(droneId: String, timestamp: Long, lat: Double, lon: Double, alt: Double)

object StreamProcessor {
  def process(frames: Seq[TelemetryFrame]): Seq[TelemetryFrame] =
    frames.filter(_.alt > 0.0).sortBy(_.timestamp)

  def aggregate(frames: Seq[TelemetryFrame]): Map[String, Int] =
    frames.groupBy(_.droneId).view.mapValues(_.size).toMap
}
