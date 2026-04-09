/** Phase 310: Scala Performance Profiler
  * Immutable benchmark history with functional combinators.
  * Pattern matching for regression classification, monadic result chaining.
  */

package sdacs.performance

import scala.collection.immutable.{Map, Vector}
import scala.math._

// ── Types ──────────────────────────────────────────────────────────
case class BenchmarkResult(
    name: String,
    metric: String,
    value: Double,
    unit: String = "ms",
    timestamp: Long = System.currentTimeMillis(),
    baseline: Option[Double] = None,
    regression: Boolean = false,
    deltaPct: Double = 0.0
)

case class BenchmarkConfig(
    name: String,
    func: () => Any,
    metric: String = "time_ms",
    unit: String = "ms",
    nRuns: Int = 10,
    baseline: Option[Double] = None,
    thresholdPct: Double = 10.0
)

sealed trait TrendDirection
case object Degrading extends TrendDirection
case object Improving extends TrendDirection
case object Stable extends TrendDirection
case object InsufficientData extends TrendDirection

case class TrendAnalysis(
    direction: TrendDirection,
    slope: Double,
    latest: Double,
    mean: Double
)

// ── Performance Profiler ───────────────────────────────────────────
class PerformanceProfiler {
  private var benchmarks: Map[String, BenchmarkConfig] = Map.empty
  private var history: Map[String, Vector[BenchmarkResult]] = Map.empty
  private var baselines: Map[String, Double] = Map.empty
  private var alerts: Vector[String] = Vector.empty

  def register(
      name: String,
      func: () => Any,
      metric: String = "time_ms",
      unit: String = "ms",
      nRuns: Int = 10,
      baseline: Option[Double] = None,
      thresholdPct: Double = 10.0
  ): Unit = {
    val config = BenchmarkConfig(name, func, metric, unit, nRuns, baseline, thresholdPct)
    benchmarks += (name -> config)
    baseline.foreach(b => baselines += (name -> b))
  }

  def run(name: String): Option[BenchmarkResult] = {
    benchmarks.get(name).map { config =>
      val measurements = (1 to config.nRuns).map { _ =>
        val start = System.nanoTime()
        val retVal = config.func()
        val elapsed = (System.nanoTime() - start) / 1e6 // ms

        config.metric match {
          case "time_ms" => elapsed
          case _ => retVal match {
            case n: Number => n.doubleValue()
            case _         => elapsed
          }
        }
      }

      val sorted = measurements.sorted
      val medianValue = if (sorted.size % 2 == 0)
        (sorted(sorted.size / 2 - 1) + sorted(sorted.size / 2)) / 2.0
      else
        sorted(sorted.size / 2)

      val baseline = baselines.get(name).orElse(config.baseline)
      val (isRegression, deltaPct) = baseline match {
        case Some(bl) if bl > 0 =>
          val delta = (medianValue - bl) / bl * 100.0
          val regressed = config.metric match {
            case "time_ms" => delta > config.thresholdPct
            case _         => delta < -config.thresholdPct
          }
          (regressed, delta)
        case _ => (false, 0.0)
      }

      val result = BenchmarkResult(
        name = name, metric = config.metric,
        value = BigDecimal(medianValue).setScale(4, BigDecimal.RoundingMode.HALF_UP).toDouble,
        unit = config.unit, baseline = baseline,
        regression = isRegression,
        deltaPct = BigDecimal(deltaPct).setScale(2, BigDecimal.RoundingMode.HALF_UP).toDouble
      )

      history += (name -> (history.getOrElse(name, Vector.empty) :+ result))

      if (isRegression) {
        alerts :+= f"REGRESSION: $name — $deltaPct%+.1f%% ($medianValue%.2f vs baseline ${baseline.getOrElse(0.0)}%.2f)"
      }

      result
    }
  }

  def runAll(): Vector[BenchmarkResult] =
    benchmarks.keys.flatMap(run).toVector

  def setBaseline(name: String, value: Double): Unit =
    baselines += (name -> value)

  def autoBaseline(name: String): Option[Double] = {
    history.get(name).flatMap { h =>
      if (h.isEmpty) None
      else {
        val recent = h.takeRight(10).map(_.value).sorted
        val median = recent(recent.size / 2)
        baselines += (name -> median)
        Some(median)
      }
    }
  }

  def getTrend(name: String): TrendAnalysis = {
    history.get(name) match {
      case Some(h) if h.size >= 3 =>
        val values = h.map(_.value)
        val n = values.size.toDouble
        val indices = (0 until values.size).map(_.toDouble)
        val sumX = indices.sum
        val sumY = values.sum
        val sumXY = indices.zip(values).map { case (x, y) => x * y }.sum
        val sumX2 = indices.map(x => x * x).sum
        val slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX)

        val direction = slope match {
          case s if s > 0.01  => Degrading
          case s if s < -0.01 => Improving
          case _              => Stable
        }

        TrendAnalysis(direction, slope, values.last, values.sum / values.size)

      case _ => TrendAnalysis(InsufficientData, 0.0, 0.0, 0.0)
    }
  }

  def getAlerts: Vector[String] = alerts
  def clearAlerts(): Unit = { alerts = Vector.empty }

  def summary: Map[String, Any] = {
    val regressions = history.values.count(h => h.nonEmpty && h.last.regression)
    Map(
      "totalBenchmarks" -> benchmarks.size,
      "totalRuns" -> history.values.map(_.size).sum,
      "baselinesSet" -> baselines.size,
      "regressionsDetected" -> regressions,
      "activeAlerts" -> alerts.size
    )
  }
}

// ── Main ───────────────────────────────────────────────────────────
object PerformanceProfilerApp extends App {
  val profiler = new PerformanceProfiler()

  profiler.register("sort_1k", () => (1000 to 1 by -1).sorted, baseline = Some(1.0))
  profiler.register("sum_10k", () => (1 to 10000).sum)
  profiler.register("fib_30", () => {
    def fib(n: Int): Int = if (n <= 1) n else fib(n - 1) + fib(n - 2)
    fib(30)
  }, baseline = Some(5.0))

  val results = profiler.runAll()
  results.foreach { r =>
    val flag = if (r.regression) " [REGRESSION]" else ""
    println(f"  ${r.name}%-15s ${r.value}%8.4f ${r.unit}%-4s delta=${r.deltaPct}%+.1f%%$flag")
  }

  println(s"\nSummary: ${profiler.summary}")
  profiler.getAlerts.foreach(a => println(s"  ALERT: $a"))
}
