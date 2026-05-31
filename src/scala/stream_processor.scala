// Stream Processor — SDACS Phase 632
package sdacs.stream

import scala.collection.mutable

case class TelemetryPacket(droneId: String, lat: Double, lon: Double, alt: Double)

class StreamProcessor {
  private val buffer = mutable.Queue[TelemetryPacket]()
  
  def ingest(packet: TelemetryPacket): Unit = buffer.enqueue(packet)
  def process(): Seq[TelemetryPacket] = buffer.dequeueAll(_ => true).toSeq
}
