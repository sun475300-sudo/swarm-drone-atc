// Phase 524: C++ Formation GAN Engine — Generator/Discriminator
#include <cstdio>
#include <cmath>
#include <vector>
#include <numeric>
#include <algorithm>

struct PRNG {
    uint64_t state;
    PRNG(uint64_t seed = 42) : state(seed ^ 0x6c62272e07bb0142ULL) {}
    uint64_t next() { state ^= state << 13; state ^= state >> 7; state ^= state << 17; return state; }
    double uniform() { return (next() & 0x7FFFFFFF) / double(0x7FFFFFFF); }
    double normal() { double u1 = std::max(uniform(), 1e-10), u2 = uniform();
                      return std::sqrt(-2*std::log(u1)) * std::cos(2*M_PI*u2); }
};

struct Matrix {
    std::vector<double> data;
    int rows, cols;
    Matrix(int r, int c) : data(r*c, 0.0), rows(r), cols(c) {}
    double& at(int i, int j) { return data[i*cols+j]; }
    double at(int i, int j) const { return data[i*cols+j]; }
    void randomize(PRNG& rng, double scale) {
        for (auto& v : data) v = rng.normal() * scale;
    }
};

Matrix matmul(const Matrix& a, const Matrix& b) {
    Matrix c(a.rows, b.cols);
    for (int i = 0; i < a.rows; i++)
        for (int j = 0; j < b.cols; j++) {
            double s = 0;
            for (int k = 0; k < a.cols; k++) s += a.at(i,k) * b.at(k,j);
            c.at(i,j) = s;
        }
    return c;
}

double sigmoid(double x) { return 1.0 / (1.0 + std::exp(-x)); }

struct Generator {
    Matrix W1, W2;
    int latent_dim, hidden, out_dim;
    Generator(int lat, int hid, int out, PRNG& rng)
        : W1(lat, hid), W2(hid, out), latent_dim(lat), hidden(hid), out_dim(out) {
        W1.randomize(rng, 0.1); W2.randomize(rng, 0.1);
    }
    std::vector<double> forward(const std::vector<double>& z) {
        Matrix zi(1, latent_dim);
        for (int i = 0; i < latent_dim; i++) zi.at(0,i) = z[i];
        auto h = matmul(zi, W1);
        for (auto& v : h.data) v = std::tanh(v);
        auto o = matmul(h, W2);
        for (auto& v : o.data) v *= 50.0;
        return o.data;
    }
    void perturb(PRNG& rng, double scale) {
        for (auto& v : W1.data) v += rng.normal() * scale;
        for (auto& v : W2.data) v += rng.normal() * scale;
    }
};

struct Discriminator {
    Matrix W1, W2;
    Discriminator(int in_dim, int hid, PRNG& rng)
        : W1(in_dim, hid), W2(hid, 1) {
        W1.randomize(rng, 0.1); W2.randomize(rng, 0.1);
    }
    double forward(const std::vector<double>& x) {
        Matrix xi(1, W1.rows);
        for (int i = 0; i < std::min((int)x.size(), W1.rows); i++) xi.at(0,i) = x[i];
        auto h = matmul(xi, W1);
        for (auto& v : h.data) v = std::tanh(v);
        auto o = matmul(h, W2);
        return sigmoid(o.data[0]);
    }
    void perturb(PRNG& rng, double scale) {
        for (auto& v : W1.data) v += rng.normal() * scale;
        for (auto& v : W2.data) v += rng.normal() * scale;
    }
};

double evaluateFormation(const std::vector<double>& pos, int n_drones) {
    double min_dist = 1e9;
    for (int i = 0; i < n_drones; i++)
        for (int j = i+1; j < n_drones; j++) {
            double dx = pos[i*3]-pos[j*3], dy = pos[i*3+1]-pos[j*3+1], dz = pos[i*3+2]-pos[j*3+2];
            min_dist = std::min(min_dist, std::sqrt(dx*dx+dy*dy+dz*dz));
        }
    double sep = std::min(1.0, min_dist/5.0);
    double cx=0,cy=0,cz=0;
    for (int i = 0; i < n_drones; i++) { cx+=pos[i*3]; cy+=pos[i*3+1]; cz+=pos[i*3+2]; }
    cx/=n_drones; cy/=n_drones; cz/=n_drones;
    double var=0;
    for (int i = 0; i < n_drones; i++) {
        double dx=pos[i*3]-cx, dy=pos[i*3+1]-cy, dz=pos[i*3+2]-cz;
        var += dx*dx+dy*dy+dz*dz;
    }
    double spread = std::min(1.0, std::sqrt(var/n_drones)/30.0);
    return 0.5*sep + 0.5*spread;
}

int main() {
    PRNG rng(42);
    int n_drones = 8, latent = 16;
    Generator gen(latent, 32, n_drones*3, rng);
    Discriminator disc(n_drones*3, 16, rng);

    for (int epoch = 0; epoch < 20; epoch++) {
        std::vector<double> z(latent);
        for (auto& v : z) v = rng.normal();
        auto fake = gen.forward(z);
        double d_score = disc.forward(fake);
        double quality = evaluateFormation(fake, n_drones);
        gen.perturb(rng, 0.005);
        disc.perturb(rng, 0.005);
        if (epoch % 5 == 0)
            printf("Epoch %2d: D=%.4f quality=%.4f\n", epoch, d_score, quality);
    }
    printf("Training complete: %d epochs\n", 20);
    return 0;
}
