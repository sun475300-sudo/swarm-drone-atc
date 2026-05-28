// Phase 495: Explainable AI (Kotlin)
// SHAP 기반 특성 중요도, 의사결정 투명성, sealed class 활용

package com.sdacs.xai

import kotlin.math.*
import kotlin.random.Random

enum class ExplanationType {
    FEATURE_IMPORTANCE, LOCAL_SURROGATE, COUNTERFACTUAL
}

data class FeatureAttribution(
    val name: String,
    val value: Double,
    val attribution: Double,
    val direction: String
)

data class Explanation(
    val type: ExplanationType,
    val decision: String,
    val confidence: Double,
    val attributions: List<FeatureAttribution>,
    val humanReadable: String = ""
)

sealed class XAIResult {
    data class Success(val explanation: Explanation) : XAIResult()
    data class Error(val message: String) : XAIResult()
}

class SHAPExplainer(
    private val modelFn: (DoubleArray) -> Double,
    private val featureNames: List<String>,
    private val seed: Int = 42
) {
    private val rng = Random(seed)
    private val nSamples = 100

    fun explain(instance: DoubleArray): List<FeatureAttribution> {
        val baseline = DoubleArray(instance.size) { 0.0 }
        val basePred = modelFn(baseline)

        return featureNames.mapIndexed { i, name ->
            val samples = (0 until nSamples).map {
                val mask = BooleanArray(instance.size) { rng.nextBoolean() }
                val withFeature = DoubleArray(instance.size) { j ->
                    if (mask[j]) instance[j] else baseline[j]
                }.also { it[i] = instance[i] }
                val withoutFeature = DoubleArray(instance.size) { j ->
                    if (mask[j]) instance[j] else baseline[j]
                }.also { it[i] = baseline[i] }
                modelFn(withFeature) - modelFn(withoutFeature)
            }
            val shapValue = samples.average()
            FeatureAttribution(
                name, instance[i],
                (shapValue * 10000).roundToInt() / 10000.0,
                if (shapValue > 0) "positive" else "negative"
            )
        }.sortedByDescending { abs(it.attribution) }
    }
}

class CounterfactualSearch(
    private val modelFn: (DoubleArray) -> Double,
    private val featureNames: List<String>,
    private val seed: Int = 42
) {
    private val rng = Random(seed)

    fun find(instance: DoubleArray, targetAbove: Double = 0.5, maxIter: Int = 500): Map<String, Any>? {
        var bestDist = Double.MAX_VALUE
        var bestResult: Map<String, Any>? = null

        repeat(maxIter) {
            val delta = DoubleArray(instance.size) { rng.nextGaussian(0.0, 0.2) }
            val candidate = DoubleArray(instance.size) { instance[it] + delta[it] }
            val pred = modelFn(candidate)
            if (pred > targetAbove) {
                val dist = sqrt(delta.sumOf { it * it })
                if (dist < bestDist) {
                    bestDist = dist
                    bestResult = mapOf(
                        "changes" to featureNames.mapIndexed { i, n -> n to delta[i] }
                            .filter { abs(it.second) > 0.05 }.toMap(),
                        "distance" to (dist * 10000).roundToInt() / 10000.0,
                        "prediction" to (pred * 10000).roundToInt() / 10000.0
                    )
                }
            }
        }
        return bestResult
    }

    private fun Random.nextGaussian(mean: Double = 0.0, std: Double = 1.0): Double {
        val u1 = nextDouble().coerceAtLeast(1e-10)
        val u2 = nextDouble()
        return mean + std * sqrt(-2.0 * ln(u1)) * cos(2.0 * PI * u2)
    }
}

class ExplainableAIEngine(private val seed: Int = 42) {
    private val decisions = mutableListOf<Explanation>()

    fun explain(
        modelFn: (DoubleArray) -> Double,
        featureNames: List<String>,
        instance: DoubleArray,
        decisionName: String = "action"
    ): XAIResult {
        return try {
            val explainer = SHAPExplainer(modelFn, featureNames, seed)
            val attributions = explainer.explain(instance)
            val prediction = modelFn(instance)
            val top3 = attributions.take(3)
            val readable = "Decision '$decisionName' (conf=${
                (prediction * 100).roundToInt() / 100.0
            }): " + top3.joinToString(", ") {
                "${it.name}=${(it.value * 100).roundToInt() / 100.0} (${it.direction})"
            }
            val explanation = Explanation(
                ExplanationType.FEATURE_IMPORTANCE,
                decisionName, prediction, attributions, readable
            )
            decisions.add(explanation)
            XAIResult.Success(explanation)
        } catch (e: Exception) {
            XAIResult.Error(e.message ?: "Unknown error")
        }
    }

    fun summary(): Map<String, Any> = mapOf(
        "decisions_explained" to decisions.size,
        "avg_confidence" to if (decisions.isNotEmpty())
            decisions.map { it.confidence }.average() else 0.0
    )
}

private fun Double.roundToInt(): Int = kotlin.math.roundToInt(this)
private fun kotlin.math.roundToInt(x: Double): Int = x.roundToInt()
