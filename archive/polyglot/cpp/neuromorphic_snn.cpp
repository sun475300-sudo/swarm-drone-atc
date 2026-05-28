/// Phase 344: C++ Neuromorphic SNN Controller
/// Leaky Integrate-and-Fire neurons with STDP learning.
/// Cache-friendly SOA layout for spike processing.

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <algorithm>
#include <numeric>
#include <random>

// ── LIF Neuron (SOA) ────────────────────────────────────────────

struct LIFParams {
    double tau_m = 20.0;      // membrane time constant (ms)
    double v_rest = -65.0;    // resting potential (mV)
    double v_thresh = -55.0;  // spike threshold (mV)
    double v_reset = -70.0;   // reset potential (mV)
    double tau_ref = 2.0;     // refractory period (ms)
};

struct NeuronLayer {
    int size;
    std::vector<double> voltage;
    std::vector<double> current;
    std::vector<double> last_spike;
    std::vector<int> spike_count;
    LIFParams params;

    NeuronLayer(int n, LIFParams p = {})
        : size(n), voltage(n, p.v_rest), current(n, 0.0),
          last_spike(n, -1e6), spike_count(n, 0), params(p) {}

    std::vector<int> step(double dt, double t) {
        std::vector<int> spiked;
        for (int i = 0; i < size; i++) {
            if (t - last_spike[i] < params.tau_ref) {
                current[i] = 0;
                continue;
            }
            double dv = (-(voltage[i] - params.v_rest) + current[i]) / params.tau_m * dt;
            voltage[i] += dv;
            current[i] = 0;

            if (voltage[i] >= params.v_thresh) {
                voltage[i] = params.v_reset;
                last_spike[i] = t;
                spike_count[i]++;
                spiked.push_back(i);
            }
        }
        return spiked;
    }
};

// ── Synapse Matrix ──────────────────────────────────────────────

struct SynapseMatrix {
    int pre_size, post_size;
    std::vector<double> weights;  // row-major [pre][post]
    double a_plus = 0.01;
    double a_minus = 0.012;
    double tau_plus = 20.0;
    double tau_minus = 20.0;
    double w_max = 5.0;

    SynapseMatrix(int pre, int post, std::mt19937& rng)
        : pre_size(pre), post_size(post), weights(pre * post) {
        std::uniform_real_distribution<double> dist(0.5, 2.0);
        for (auto& w : weights) w = dist(rng);
    }

    double& at(int pre, int post) { return weights[pre * post_size + post]; }
    double at(int pre, int post) const { return weights[pre * post_size + post]; }

    void propagate(const std::vector<int>& spiked, NeuronLayer& post_layer) const {
        for (int pre : spiked) {
            for (int j = 0; j < post_size; j++) {
                post_layer.current[j] += at(pre, j);
            }
        }
    }

    void stdp_update(const std::vector<int>& pre_spikes,
                     const std::vector<int>& post_spikes,
                     double t) {
        // Simplified: same-timestep potentiation
        for (int pre : pre_spikes) {
            for (int post : post_spikes) {
                double& w = at(pre, post);
                w += a_plus;
                if (w > w_max) w = w_max;
            }
        }
    }
};

// ── SNN Controller ──────────────────────────────────────────────

struct ControlOutput {
    double roll, pitch, yaw, thrust;
};

class SNNController {
    NeuronLayer input_layer;
    NeuronLayer hidden_layer;
    NeuronLayer output_layer;
    SynapseMatrix syn_ih;
    SynapseMatrix syn_ho;
    std::mt19937 rng;
    double dt = 0.5;
    double current_time = 0;
    int step_count = 0;
    int total_spikes = 0;

public:
    SNNController(int n_input = 6, int n_hidden = 20, int n_output = 4,
                  unsigned seed = 42)
        : input_layer(n_input), hidden_layer(n_hidden), output_layer(n_output),
          syn_ih(n_input, n_hidden, rng), syn_ho(n_hidden, n_output, rng),
          rng(seed) {}

    void encode_input(const std::vector<double>& values) {
        std::normal_distribution<double> noise(0, 0.5);
        for (int i = 0; i < input_layer.size && i < (int)values.size(); i++) {
            input_layer.current[i] = values[i] * 15.0 + noise(rng);
        }
    }

    ControlOutput control_step(double roll_err, double pitch_err,
                               double yaw_err, double alt_err,
                               double vx_err, double vy_err) {
        encode_input({roll_err, pitch_err, yaw_err, alt_err, vx_err, vy_err});
        current_time += dt;
        step_count++;

        auto in_spikes = input_layer.step(dt, current_time);
        total_spikes += in_spikes.size();
        syn_ih.propagate(in_spikes, hidden_layer);

        auto hid_spikes = hidden_layer.step(dt, current_time);
        total_spikes += hid_spikes.size();
        syn_ho.propagate(hid_spikes, output_layer);

        auto out_spikes = output_layer.step(dt, current_time);
        total_spikes += out_spikes.size();

        // STDP on hidden→output
        syn_ho.stdp_update(hid_spikes, out_spikes, current_time);

        // Convert spike rates to control
        double scale = 0.01;
        double time_s = std::max(current_time / 1000.0, 0.001);
        return {
            output_layer.spike_count[0] / time_s * scale,
            output_layer.spike_count[1] / time_s * scale,
            output_layer.spike_count[2] / time_s * scale,
            output_layer.spike_count[3] / time_s * scale,
        };
    }

    void print_summary() const {
        printf("SNN Controller | Layers: %d-%d-%d | Steps: %d | "
               "Spikes: %d | SimTime: %.1fms\n",
               input_layer.size, hidden_layer.size, output_layer.size,
               step_count, total_spikes, current_time);

        // Weight stats
        const auto& w = syn_ho.weights;
        double sum = std::accumulate(w.begin(), w.end(), 0.0);
        double mean = sum / w.size();
        double sq_sum = std::inner_product(w.begin(), w.end(), w.begin(), 0.0);
        double stddev = std::sqrt(sq_sum / w.size() - mean * mean);
        printf("Weights H→O: mean=%.4f std=%.4f\n", mean, stddev);
    }
};

// ── Main ────────────────────────────────────────────────────────

int main() {
    SNNController ctrl(6, 20, 4, 42);

    for (int t = 0; t < 100; t++) {
        double roll_err = std::sin(t * 0.1) * 5.0;
        double pitch_err = std::cos(t * 0.1) * 3.0;
        auto cmd = ctrl.control_step(roll_err, pitch_err, 0.5, 2.0, 1.0, -0.5);
        if (t % 25 == 0) {
            printf("t=%3d | roll=%.4f pitch=%.4f yaw=%.4f thrust=%.4f\n",
                   t, cmd.roll, cmd.pitch, cmd.yaw, cmd.thrust);
        }
    }

    ctrl.print_summary();
    return 0;
}
