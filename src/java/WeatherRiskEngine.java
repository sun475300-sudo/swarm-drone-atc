/*
 * SDACS weather risk model (Java).
 * Formula parity with simulation/weather_risk_model.py
 */

public final class WeatherRiskEngine {
    private WeatherRiskEngine() {}

    public static final class Input {
        public final double windMps;
        public final double visibilityKm;
        public final double precipitationLevel;
        public final double congestion;

        public Input(double windMps, double visibilityKm, double precipitationLevel, double congestion) {
            this.windMps = windMps;
            this.visibilityKm = visibilityKm;
            this.precipitationLevel = precipitationLevel;
            this.congestion = congestion;
        }
    }

    public static final class Output {
        public final double score;
        public final String category;

        public Output(double score, String category) {
            this.score = score;
            this.category = category;
        }
    }

    private static double clamp(double v, double lo, double hi) {
        return Math.max(lo, Math.min(hi, v));
    }

    public static Output compute(Input input) {
        double windNorm = clamp(input.windMps / 20.0, 0.0, 1.0);
        double visNorm = clamp(input.visibilityKm / 10.0, 0.0, 1.0);
        double visPenalty = 1.0 - visNorm;
        double precip = clamp(input.precipitationLevel, 0.0, 1.0);
        double congestion = clamp(input.congestion, 0.0, 1.0);

        double raw = 0.35 * windNorm + 0.25 * visPenalty + 0.20 * precip + 0.20 * congestion;
        double score = Math.round(clamp(raw, 0.0, 1.0) * 10000.0) / 10000.0;

        String category;
        if (score < 0.25) {
            category = "GREEN";
        } else if (score < 0.50) {
            category = "YELLOW";
        } else if (score < 0.75) {
            category = "ORANGE";
        } else {
            category = "RED";
        }

        return new Output(score, category);
    }
}
