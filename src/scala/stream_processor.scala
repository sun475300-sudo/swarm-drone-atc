// Phase 632 — Telemetry Stream Processor (Scala)
// Akka Streams 기반 드론 텔레메트리 실시간 처리 파이프라인

package sdacs.stream

import scala.collection.mutable

case class TelemetryFrame(
    droneId: String,
    timestamp: Double,
    x: Double,
    y: Double,
    z: Double,
    vx: Double,
    vy: Double,
    vz: Double,
    batteryPct: Double
)

case class ConflictAlert(
    droneA: String,
    droneB: String,
    distanceM: Double,
    timestamp: Double
)

object StreamProcessor {

  val SAFE_SEPARATION_M: Double = 30.0

  /** 텔레메트리 프레임 스트림에서 충돌 후보 쌍을 추출한다. */
  def detectConflicts(
      frames: Seq[TelemetryFrame]
  ): Seq[ConflictAlert] = {
    val alerts = mutable.ArrayBuffer.empty[ConflictAlert]
    val indexed = frames.groupBy(_.timestamp)

    for ((ts, group) <- indexed) {
      val arr = group.toArray
      for {
        i <- arr.indices
        j <- (i + 1) until arr.length
      } {
        val a = arr(i)
        val b = arr(j)
        val dist = math.sqrt(
          math.pow(a.x - b.x, 2) +
          math.pow(a.y - b.y, 2) +
          math.pow(a.z - b.z, 2)
        )
        if (dist < SAFE_SEPARATION_M)
          alerts += ConflictAlert(a.droneId, b.droneId, dist, ts)
      }
    }
    alerts.toSeq
  }

  /** 단순 이동 평균으로 배터리 잔량 스무딩. */
  def smoothBattery(
      frames: Seq[TelemetryFrame],
      windowSize: Int = 5
  ): Seq[TelemetryFrame] =
    frames.zipWithIndex.map { case (f, idx) =>
      val window = frames.slice(math.max(0, idx - windowSize + 1), idx + 1)
      val avg    = window.map(_.batteryPct).sum / window.size
      f.copy(batteryPct = avg)
    }
}
