// SDACS Stream Processor — Scala
// 드론 텔레메트리 실시간 스트림 처리

package sdacs.stream

import scala.collection.mutable
import scala.math._

case class TelemetryFrame(
  droneId: String,
  timestamp: Double,
  x: Double,
  y: Double,
  z: Double,
  vx: Double,
  vy: Double,
  vz: Double,
  battery: Double
)

case class ConflictAlert(
  droneA: String,
  droneB: String,
  distance: Double,
  timeToConflict: Double,
  severity: String
)

case class StreamStats(
  totalFrames: Long,
  conflictsDetected: Int,
  avgBattery: Double,
  maxAltitude: Double,
  throughputFps: Double
)

class TelemetryStreamProcessor(windowSize: Int = 100) {
  private val buffer = mutable.Queue[TelemetryFrame]()
  private val latestState = mutable.Map[String, TelemetryFrame]()
  private var framesProcessed: Long = 0L
  private var conflictsDetected: Int = 0
  private val startTime: Long = System.currentTimeMillis()

  val SEPARATION_THRESHOLD = 50.0

  def ingest(frame: TelemetryFrame): Unit = {
    buffer.enqueue(frame)
    if (buffer.size > windowSize) buffer.dequeue()
    latestState(frame.droneId) = frame
    framesProcessed += 1
  }

  def detectConflicts(): Seq[ConflictAlert] = {
    val drones = latestState.values.toSeq
    val alerts = mutable.ListBuffer[ConflictAlert]()

    for {
      i <- drones.indices
      j <- (i + 1) until drones.size
    } {
      val a = drones(i)
      val b = drones(j)
      val dist = distance3d(a, b)
      if (dist < SEPARATION_THRESHOLD) {
        val ttc = timeToClosestApproach(a, b)
        val severity = if (dist < 20.0) "CRITICAL" else if (dist < 35.0) "HIGH" else "MEDIUM"
        alerts += ConflictAlert(a.droneId, b.droneId, dist, ttc, severity)
        conflictsDetected += 1
      }
    }
    alerts.toSeq
  }

  private def distance3d(a: TelemetryFrame, b: TelemetryFrame): Double = {
    sqrt(pow(a.x - b.x, 2) + pow(a.y - b.y, 2) + pow(a.z - b.z, 2))
  }

  private def timeToClosestApproach(a: TelemetryFrame, b: TelemetryFrame): Double = {
    val dx = b.x - a.x; val dy = b.y - a.y
    val dvx = b.vx - a.vx; val dvy = b.vy - a.vy
    val dvSq = dvx * dvx + dvy * dvy
    if (dvSq < 1e-6) Double.MaxValue
    else math.max(0.0, -(dx * dvx + dy * dvy) / dvSq)
  }

  def stats(): StreamStats = {
    val elapsed = (System.currentTimeMillis() - startTime) / 1000.0
    val batteries = latestState.values.map(_.battery)
    val avgBat = if (batteries.isEmpty) 0.0 else batteries.sum / batteries.size
    val maxAlt = if (latestState.isEmpty) 0.0 else latestState.values.map(_.z).max
    StreamStats(
      framesProcessed,
      conflictsDetected,
      avgBat,
      maxAlt,
      if (elapsed > 0) framesProcessed / elapsed else 0.0
    )
  }

  def windowedAvgAltitude(): Double = {
    if (buffer.isEmpty) return 0.0
    buffer.map(_.z).sum / buffer.size
  }

  def activeDrones(): Set[String] = latestState.keySet.toSet

  def lowBatteryDrones(threshold: Double = 20.0): Seq[String] =
    latestState.values.filter(_.battery < threshold).map(_.droneId).toSeq
}

object StreamProcessor {
  def buildPipeline(capacity: Int = 1000): TelemetryStreamProcessor =
    new TelemetryStreamProcessor(capacity)
}
