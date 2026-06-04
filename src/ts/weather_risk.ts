/**
 * SDACS weather risk model (TypeScript).
 * Mirrors the canonical Python formula for cross-language consistency.
 */

export interface WeatherRiskInput {
  windMps: number;
  visibilityKm: number;
  precipitationLevel: number;
  congestion: number;
}

export interface WeatherRiskOutput {
  score: number;
  category: "GREEN" | "YELLOW" | "ORANGE" | "RED";
}

const clamp = (v: number, lo: number, hi: number): number =>
  Math.max(lo, Math.min(hi, v));

export function computeWeatherRisk(input: WeatherRiskInput): WeatherRiskOutput {
  const windNorm = clamp(input.windMps / 20.0, 0, 1);
  const visNorm = clamp(input.visibilityKm / 10.0, 0, 1);
  const visPenalty = 1.0 - visNorm;
  const precip = clamp(input.precipitationLevel, 0, 1);
  const congestion = clamp(input.congestion, 0, 1);

  const raw = 0.35 * windNorm + 0.25 * visPenalty + 0.2 * precip + 0.2 * congestion;
  const score = Math.round(clamp(raw, 0, 1) * 10000) / 10000;

  let category: WeatherRiskOutput["category"] = "RED";
  if (score < 0.25) category = "GREEN";
  else if (score < 0.5) category = "YELLOW";
  else if (score < 0.75) category = "ORANGE";

  return { score, category };
}
