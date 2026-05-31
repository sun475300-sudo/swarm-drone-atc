// P632: Stream Processor - Scala stub
// Processes real-time drone telemetry streams

package com.sdacs.stream

import scala.collection.mutable

case class TelemetryFrame(
  droneId: String,
  timestamp: Long,
  position: (Double, Double, Double),
  velocity: (Double, Double, Double),
  battery: Double
)

class StreamProcessor(bufferSize: Int = 1000) {
  private val buffer = mutable.Queue[TelemetryFrame]()
  private var processedCount = 0L

  def ingest(frame: TelemetryFrame): Unit = {
    if (buffer.size >= bufferSize) buffer.dequeue()
    buffer.enqueue(frame)
    processedCount += 1
  }

  def getStats(): Map[String, Any] = Map(
    "buffered" -> buffer.size,
    "processed" -> processedCount
  )

  def flush(): Seq[TelemetryFrame] = {
    val frames = buffer.toSeq
    buffer.clear()
    frames
  }
}

object StreamProcessor {
  def apply(bufferSize: Int = 1000): StreamProcessor = new StreamProcessor(bufferSize)
}
