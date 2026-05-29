// Phase 632: Stream Processor — Scala Akka-style Telemetry Pipeline
// 실시간 텔레메트리 스트림 파이프라인

package com.sdacs.stream

case class TelemetryEvent(
  droneId: String,
  timestamp: Long,
  x: Double,
  y: Double,
  z: Double,
  battery: Double,
  eventType: String
)

case class WindowResult(
  windowStart: Long,
  windowEnd: Long,
  count: Int,
  avgBattery: Double,
  minAltitude: Double,
  maxAltitude: Double,
  anomalyCount: Int
)

class TumblingWindow(val windowSize: Long) {
  private var buffer: List[TelemetryEvent] = Nil
  private var windowStart: Long = 0
  private var results: List[WindowResult] = Nil

  def process(event: TelemetryEvent): Option[WindowResult] = {
    if (buffer.isEmpty) {
      windowStart = event.timestamp
    }

    buffer = buffer :+ event

    if (event.timestamp - windowStart >= windowSize) {
      val result = aggregate()
      results = results :+ result
      buffer = Nil
      Some(result)
    } else {
      None
    }
  }

  private def aggregate(): WindowResult = {
    val count = buffer.length
    val avgBat = if (count > 0) buffer.map(_.battery).sum / count else 0.0
    val minAlt = if (count > 0) buffer.map(_.z).min else 0.0
    val maxAlt = if (count > 0) buffer.map(_.z).max else 0.0
    val anomalies = buffer.count(e => e.battery < 0.15 || e.z > 120.0 || e.z < 0.0)

    WindowResult(
      windowStart = windowStart,
      windowEnd = buffer.lastOption.map(_.timestamp).getOrElse(windowStart),
      count = count,
      avgBattery = avgBat,
      minAltitude = minAlt,
      maxAltitude = maxAlt,
      anomalyCount = anomalies
    )
  }

  def getResults: List[WindowResult] = results
}

class StreamProcessor(windowSize: Long = 5000) {
  private val window = new TumblingWindow(windowSize)
  private var processedCount: Int = 0
  private var totalAnomalies: Int = 0

  def ingest(event: TelemetryEvent): Option[WindowResult] = {
    processedCount += 1
    val result = window.process(event)
    result.foreach(r => totalAnomalies += r.anomalyCount)
    result
  }

  def summary: Map[String, Any] = Map(
    "processed" -> processedCount,
    "windows" -> window.getResults.length,
    "totalAnomalies" -> totalAnomalies
  )
}
