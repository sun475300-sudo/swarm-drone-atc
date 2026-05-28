/**
 * SDACS Monte Carlo 시뮬레이션 엔진 — Scala
 * ============================================
 * 함수형 프로그래밍 + 병렬 컬렉션 기반 MC 검증
 *
 * 기능:
 *   - 파라미터 그리드 생성
 *   - 병렬 시뮬레이션 실행
 *   - 통계 집계 (평균/분산/CI)
 *   - SLA 합격 판정
 */

package com.sdacs.montecarlo

import scala.util.Random
import scala.collection.parallel.CollectionConverters._

case class SimConfig(
  droneCount: Int,
  windSpeed: Double,
  failureRate: Double,
  duration: Double,
  seed: Long
)

case class SimResult(
  config: SimConfig,
  collisionRate: Double,
  resolutionRate: Double,
  avgResponseTime: Double,
  p99Latency: Double,
  avgBattery: Double,
  slaPass: Boolean
)

case class MCStats(
  runs: Int,
  avgCollisionRate: Double,
  stdCollisionRate: Double,
  slaPassRate: Double,
  ci95Lower: Double,
  ci95Upper: Double,
  worstCollisionRate: Double,
  bestCollisionRate: Double
)

object MonteCarloEngine {

  /** 파라미터 그리드 생성 */
  def generateGrid(
    droneCounts: Seq[Int] = Seq(10, 50, 100, 200),
    windSpeeds: Seq[Double] = Seq(0, 5, 10, 15, 20),
    failureRates: Seq[Double] = Seq(0, 0.05, 0.1),
    duration: Double = 300.0,
    seedsPerConfig: Int = 100
  ): Seq[SimConfig] = {
    for {
      dc <- droneCounts
      ws <- windSpeeds
      fr <- failureRates
      seed <- 1 to seedsPerConfig
    } yield SimConfig(dc, ws, fr, duration, seed.toLong)
  }

  /** 단일 시뮬레이션 실행 (간이 모델) */
  def runSingle(config: SimConfig): SimResult = {
    val rng = new Random(config.seed)

    // 간이 충돌 모델: 드론 수^2에 비례, 풍속/장애율로 증가
    val baseRate = config.droneCount * config.droneCount * 0.00001
    val windFactor = 1.0 + config.windSpeed * 0.05
    val failureFactor = 1.0 + config.failureRate * 2.0
    val noise = rng.nextGaussian() * 0.001

    val collisionRate = math.max(0, baseRate * windFactor * failureFactor + noise)
    val resolutionRate = math.min(1.0, 1.0 - collisionRate * 100)
    val avgResponse = 0.3 + config.droneCount * 0.002 + config.windSpeed * 0.01 + rng.nextGaussian() * 0.05
    val p99 = avgResponse * 3.0 + rng.nextGaussian() * 0.1
    val avgBattery = 85.0 - config.duration / 60.0 * 5.0 - config.windSpeed * 0.5

    val slaPass = collisionRate < 0.001 &&
                  resolutionRate > 0.95 &&
                  avgResponse < 2.0 &&
                  p99 < 5.0

    SimResult(config, collisionRate, resolutionRate, avgResponse, p99, avgBattery, slaPass)
  }

  /** 병렬 실행 + 통계 집계 */
  def runAll(configs: Seq[SimConfig]): MCStats = {
    val results = configs.par.map(runSingle).seq

    val rates = results.map(_.collisionRate)
    val n = rates.length.toDouble
    val mean = rates.sum / n
    val variance = rates.map(r => math.pow(r - mean, 2)).sum / n
    val std = math.sqrt(variance)
    val slaPassRate = results.count(_.slaPass).toDouble / n

    // 95% 신뢰구간
    val z = 1.96
    val margin = z * std / math.sqrt(n)

    MCStats(
      runs = results.length,
      avgCollisionRate = mean,
      stdCollisionRate = std,
      slaPassRate = slaPassRate,
      ci95Lower = mean - margin,
      ci95Upper = mean + margin,
      worstCollisionRate = rates.max,
      bestCollisionRate = rates.min
    )
  }

  /** 빠른 검증 (소규모) */
  def quickCheck(droneCount: Int = 50, runs: Int = 100): MCStats = {
    val configs = (1 to runs).map(s =>
      SimConfig(droneCount, 5.0, 0.05, 300.0, s.toLong)
    )
    runAll(configs)
  }

  /** SLA 준수 여부 판정 */
  def slaVerdict(stats: MCStats, threshold: Double = 0.95): String = {
    if (stats.slaPassRate >= threshold) s"PASS (${stats.slaPassRate * 100}%)"
    else s"FAIL (${stats.slaPassRate * 100}% < ${threshold * 100}%)"
  }

  def main(args: Array[String]): Unit = {
    println("=== SDACS Monte Carlo Engine (Scala) ===")
    val configs = generateGrid(seedsPerConfig = 10)
    println(s"총 설정: ${configs.length}")
    val stats = runAll(configs)
    println(s"결과: ${stats}")
    println(s"SLA 판정: ${slaVerdict(stats)}")
  }
}
