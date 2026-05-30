// Phase 632 — Scala Stream Processor for Drone Telemetry
package sdacs.stream

case class TelemetryFrame(droneId: String, x: Double, y: Double, z: Double, timestamp: Long)

object StreamProcessor {
  def process(frames: LazyList[TelemetryFrame]): LazyList[TelemetryFrame] =
    frames.filter(_.z >= 0).map(f => f.copy(timestamp = f.timestamp / 1000))

  def detectConflicts(frames: LazyList[TelemetryFrame], threshold: Double): LazyList[(String, String)] =
    frames.sliding(2).collect {
      case LazyList(a, b) if a.droneId != b.droneId &&
        math.sqrt(math.pow(a.x-b.x,2)+math.pow(a.y-b.y,2)+math.pow(a.z-b.z,2)) < threshold =>
        (a.droneId, b.droneId)
    }.to(LazyList)
}
