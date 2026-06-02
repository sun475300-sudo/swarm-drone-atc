// Phase 632: Stream Processor — Scala
// SDACS real-time event stream processing for drone telemetry

package sdacs.streaming

import scala.collection.mutable

case class TelemetryEvent(droneId: String, battery: Double, altitude: Double,
                           speed: Double, timestamp: Long = System.currentTimeMillis())

case class AlertEvent(droneId: String, severity: String, message: String,
                      timestamp: Long = System.currentTimeMillis())

trait StreamProcessor[In, Out] {
  def process(event: In): Option[Out]
  def flush(): Seq[Out] = Seq.empty
}

class BatteryAlertProcessor(threshold: Double = 20.0)
    extends StreamProcessor[TelemetryEvent, AlertEvent] {
  def process(e: TelemetryEvent): Option[AlertEvent] =
    if (e.battery < threshold)
      Some(AlertEvent(e.droneId, "WARNING", f"Battery low: ${e.battery}%.1f%%"))
    else None
}

class StreamPipeline[A, B, C](first: StreamProcessor[A, B], second: StreamProcessor[B, C]) {
  def process(event: A): Option[C] = first.process(event).flatMap(second.process)
}

class StreamAggregator {
  private val window = mutable.Queue[TelemetryEvent]()
  private val size   = 10

  def add(e: TelemetryEvent): Unit = { window.enqueue(e); if (window.size > size) window.dequeue() }
  def avgBattery: Double = if (window.isEmpty) 0.0 else window.map(_.battery).sum / window.size
  def stats: Map[String, Any] = Map("count" -> window.size, "avg_battery" -> avgBattery)
}

object StreamProcessorDemo extends App {
  val processor = new BatteryAlertProcessor(20.0)
  val agg = new StreamAggregator()
  val events = List(
    TelemetryEvent("D001", 85.0, 60.0, 10.0),
    TelemetryEvent("D002", 15.0, 55.0,  8.0),
    TelemetryEvent("D003", 92.0, 70.0, 12.0),
  )
  events.foreach { e =>
    agg.add(e)
    processor.process(e).foreach(a => println(s"Alert: ${a.message}"))
  }
  println(s"Phase 632: Stream stats: ${agg.stats}")
}
