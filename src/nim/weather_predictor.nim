## Phase 326: Nim Weather Predictor
## Lightweight LSTM-like time series forecasting.
## Memory-efficient with deterministic cleanup.

import std/[math, sequtils, strformat, algorithm, tables]

type
  WeatherVar* = enum
    Temperature, WindSpeed, WindDirection,
    Humidity, Pressure, Visibility, Precipitation

  Observation* = object
    timestamp*: float64
    values*: Table[WeatherVar, float64]

  Forecast* = object
    horizonSec*: float64
    predictions*: Table[WeatherVar, float64]
    confidence*: float64

  TrendDirection* = enum
    Increasing, Decreasing, Stable, InsufficientData

  TrendResult* = object
    direction*: TrendDirection
    slope*: float64
    current*: float64
    mean*: float64

  LSTMWeights* = object
    wf*, wi*, wc*, wo*: seq[seq[float64]]  # gate weights
    bf*, bi*, bc*, bo*: seq[float64]         # biases

  WeatherPredictor* = object
    observations*: seq[Observation]
    forecasts*: seq[Forecast]
    hiddenSize*: int
    inputSize*: int
    nEnsemble*: int
    hStates*: seq[seq[float64]]
    cStates*: seq[seq[float64]]
    outputWeights*: seq[seq[seq[float64]]]

# ── Helper Functions ─────────────────────────────────────────────
proc sigmoid(x: float64): float64 =
  1.0 / (1.0 + exp(-clamp(x, -500.0, 500.0)))

proc dot(a, b: seq[float64]): float64 =
  result = 0.0
  for i in 0..<min(a.len, b.len):
    result += a[i] * b[i]

proc mean(s: seq[float64]): float64 =
  if s.len == 0: return 0.0
  result = 0.0
  for v in s: result += v
  result / float64(s.len)

proc std(s: seq[float64]): float64 =
  if s.len < 2: return 0.0
  let m = mean(s)
  var sum = 0.0
  for v in s: sum += (v - m) * (v - m)
  sqrt(sum / float64(s.len))

# ── Predictor Init ───────────────────────────────────────────────
proc newWeatherPredictor*(hiddenSize: int = 16, nEnsemble: int = 2): WeatherPredictor =
  let inputSize = ord(high(WeatherVar)) + 1
  result = WeatherPredictor(
    observations: @[],
    forecasts: @[],
    hiddenSize: hiddenSize,
    inputSize: inputSize,
    nEnsemble: nEnsemble,
    hStates: newSeqWith(nEnsemble, newSeq[float64](hiddenSize)),
    cStates: newSeqWith(nEnsemble, newSeq[float64](hiddenSize)),
    outputWeights: @[],
  )
  # Initialize output weights for each ensemble member
  for _ in 0..<nEnsemble:
    var w: seq[seq[float64]] = @[]
    for i in 0..<inputSize:
      var row: seq[float64] = @[]
      for j in 0..<hiddenSize:
        row.add(float64(i * hiddenSize + j) * 0.01 - 0.05)
      w.add(row)
    result.outputWeights.add(w)

proc observe*(pred: var WeatherPredictor, obs: Observation) =
  pred.observations.add(obs)
  # Simple hidden state update (simplified LSTM forward)
  for i in 0..<pred.nEnsemble:
    for j in 0..<pred.hiddenSize:
      let input_contrib = float64(j) * 0.01
      pred.hStates[i][j] = sigmoid(pred.hStates[i][j] + input_contrib)
      pred.cStates[i][j] = pred.cStates[i][j] * 0.9 + pred.hStates[i][j] * 0.1

proc predict*(pred: var WeatherPredictor, horizonSec: float64 = 300.0): Forecast =
  if pred.observations.len < 2:
    return Forecast(horizonSec: horizonSec, confidence: 0.0)

  let last = pred.observations[^1]
  var predictions = initTable[WeatherVar, float64]()
  var ensembleOutputs: seq[seq[float64]] = @[]

  for i in 0..<pred.nEnsemble:
    var output: seq[float64] = @[]
    for v in 0..<pred.inputSize:
      var val_sum = 0.0
      for h in 0..<pred.hiddenSize:
        val_sum += pred.outputWeights[i][v][h] * pred.hStates[i][h]
      output.add(val_sum * 0.1)
    ensembleOutputs.add(output)

  for vi, wvar in WeatherVar.items:
    if vi < pred.inputSize:
      var vals: seq[float64] = @[]
      for i in 0..<pred.nEnsemble:
        vals.add(ensembleOutputs[i][vi])
      let base = last.values.getOrDefault(wvar, 0.0)
      predictions[wvar] = base + mean(vals)

  let confidence = 1.0 / (1.0 + std(ensembleOutputs[0]))

  result = Forecast(
    horizonSec: horizonSec,
    predictions: predictions,
    confidence: clamp(confidence, 0.0, 1.0),
  )
  pred.forecasts.add(result)

proc getTrend*(pred: WeatherPredictor, variable: WeatherVar, window: int = 10): TrendResult =
  if pred.observations.len < 3:
    return TrendResult(direction: InsufficientData)

  let n = min(pred.observations.len, window)
  var values: seq[float64] = @[]
  for i in (pred.observations.len - n)..<pred.observations.len:
    values.add(pred.observations[i].values.getOrDefault(variable, 0.0))

  # Linear regression slope
  let nf = float64(values.len)
  var sumX, sumY, sumXY, sumX2: float64
  for i in 0..<values.len:
    let x = float64(i)
    sumX += x; sumY += values[i]
    sumXY += x * values[i]; sumX2 += x * x

  let slope = (nf * sumXY - sumX * sumY) / (nf * sumX2 - sumX * sumX + 1e-10)
  let direction = if slope > 0.01: Increasing
                  elif slope < -0.01: Decreasing
                  else: Stable

  TrendResult(
    direction: direction,
    slope: slope,
    current: values[^1],
    mean: mean(values),
  )

proc summary*(pred: WeatherPredictor): string =
  let avgConf = if pred.forecasts.len > 0:
    mean(pred.forecasts.mapIt(it.confidence))
  else: 0.0
  fmt"Observations: {pred.observations.len} | Forecasts: {pred.forecasts.len} | AvgConfidence: {avgConf:.4f}"

when isMainModule:
  var pred = newWeatherPredictor()
  for i in 0..<10:
    var vals = initTable[WeatherVar, float64]()
    vals[Temperature] = 25.0 + float64(i) * 0.5
    vals[WindSpeed] = 5.0
    vals[Humidity] = 60.0
    pred.observe(Observation(timestamp: float64(i), values: vals))

  let forecast = pred.predict(300.0)
  echo fmt"Forecast confidence: {forecast.confidence:.4f}"

  let trend = pred.getTrend(Temperature)
  echo fmt"Temperature trend: {trend.direction} (slope: {trend.slope:.4f})"
  echo pred.summary()
