/**
 * Phase 289: C++ Mesh Network Optimizer — 고성능 메시 네트워크 최적화
 * SIMD 가능 거리 계산, Dijkstra 최단경로, 토폴로지 관리.
 */

#include <cmath>
#include <vector>
#include <string>
#include <unordered_map>
#include <queue>
#include <limits>
#include <algorithm>

namespace sdacs {
namespace mesh {

struct Vec3 {
    double x, y, z;
    Vec3() : x(0), y(0), z(0) {}
    Vec3(double x, double y, double z) : x(x), y(y), z(z) {}

    double distance(const Vec3& other) const {
        double dx = x - other.x, dy = y - other.y, dz = z - other.z;
        return std::sqrt(dx*dx + dy*dy + dz*dz);
    }
};

enum class LinkQuality { EXCELLENT, GOOD, FAIR, POOR, DISCONNECTED };

struct MeshNode {
    std::string id;
    Vec3 position;
    bool is_relay;
    double tx_power_dbm;
    double bandwidth_mbps;
    std::vector<std::string> neighbors;

    MeshNode() : is_relay(false), tx_power_dbm(20.0), bandwidth_mbps(10.0) {}
};

struct MeshLink {
    std::string node_a, node_b;
    double distance_m;
    double rssi_dbm;
    LinkQuality quality;
    double throughput_mbps;
    double latency_ms;
};

class PathLossModel {
public:
    static constexpr double FREQ_GHZ = 2.4;
    static constexpr double C = 3e8;

    static double free_space_loss(double distance_m) {
        if (distance_m <= 0) return 0.0;
        double wavelength = C / (FREQ_GHZ * 1e9);
        return 20.0 * std::log10(4.0 * M_PI * distance_m / wavelength);
    }

    static double rssi(double tx_power, double distance_m) {
        return tx_power - free_space_loss(distance_m);
    }

    static LinkQuality quality_from_rssi(double rssi_dbm) {
        if (rssi_dbm > -50) return LinkQuality::EXCELLENT;
        if (rssi_dbm > -70) return LinkQuality::GOOD;
        if (rssi_dbm > -80) return LinkQuality::FAIR;
        if (rssi_dbm > -90) return LinkQuality::POOR;
        return LinkQuality::DISCONNECTED;
    }

    static double throughput(double rssi_dbm, double bandwidth) {
        if (rssi_dbm < -90) return 0.0;
        double snr = rssi_dbm + 90.0;
        double efficiency = std::min(1.0, std::max(0.1, snr / 40.0));
        return bandwidth * efficiency;
    }
};

class MeshNetworkOptimizer {
    std::unordered_map<std::string, MeshNode> nodes_;
    std::vector<MeshLink> links_;
    static constexpr double MAX_RANGE_M = 500.0;

public:
    void add_node(const MeshNode& node) {
        nodes_[node.id] = node;
    }

    void update_topology() {
        links_.clear();
        std::vector<std::string> ids;
        for (auto& [id, _] : nodes_) ids.push_back(id);

        for (auto& [_, node] : nodes_) node.neighbors.clear();

        for (size_t i = 0; i < ids.size(); ++i) {
            for (size_t j = i + 1; j < ids.size(); ++j) {
                auto& na = nodes_[ids[i]];
                auto& nb = nodes_[ids[j]];
                double dist = na.position.distance(nb.position);
                if (dist > MAX_RANGE_M) continue;

                double rssi = PathLossModel::rssi(na.tx_power_dbm, dist);
                auto quality = PathLossModel::quality_from_rssi(rssi);
                if (quality == LinkQuality::DISCONNECTED) continue;

                double tp = PathLossModel::throughput(rssi,
                    std::min(na.bandwidth_mbps, nb.bandwidth_mbps));
                double latency = dist / 3e8 * 1000.0 + 1.0;

                MeshLink link;
                link.node_a = ids[i];
                link.node_b = ids[j];
                link.distance_m = dist;
                link.rssi_dbm = rssi;
                link.quality = quality;
                link.throughput_mbps = tp;
                link.latency_ms = latency;
                links_.push_back(link);

                na.neighbors.push_back(ids[j]);
                nb.neighbors.push_back(ids[i]);
            }
        }
    }

    std::vector<std::string> find_route(const std::string& src, const std::string& dst) {
        using PQEntry = std::pair<double, std::string>;
        std::unordered_map<std::string, double> dist;
        std::unordered_map<std::string, std::string> prev;
        std::priority_queue<PQEntry, std::vector<PQEntry>, std::greater<>> pq;

        dist[src] = 0.0;
        pq.push({0.0, src});

        while (!pq.empty()) {
            auto [d, u] = pq.top(); pq.pop();
            if (u == dst) break;
            if (d > dist[u]) continue;

            auto it = nodes_.find(u);
            if (it == nodes_.end()) continue;

            for (const auto& nb : it->second.neighbors) {
                double link_cost = 1.0;  // simplified
                for (const auto& l : links_) {
                    if ((l.node_a == u && l.node_b == nb) ||
                        (l.node_a == nb && l.node_b == u)) {
                        link_cost = l.latency_ms;
                        break;
                    }
                }
                double nd = dist[u] + link_cost;
                if (dist.find(nb) == dist.end() || nd < dist[nb]) {
                    dist[nb] = nd;
                    prev[nb] = u;
                    pq.push({nd, nb});
                }
            }
        }

        std::vector<std::string> path;
        if (dist.find(dst) == dist.end()) return path;
        std::string node = dst;
        while (!node.empty()) {
            path.push_back(node);
            auto it = prev.find(node);
            node = (it != prev.end()) ? it->second : "";
        }
        std::reverse(path.begin(), path.end());
        return path;
    }

    double connectivity() {
        if (nodes_.size() <= 1) return 1.0;
        // BFS
        auto start = nodes_.begin()->first;
        std::unordered_map<std::string, bool> visited;
        std::queue<std::string> q;
        q.push(start);
        visited[start] = true;
        while (!q.empty()) {
            auto curr = q.front(); q.pop();
            for (const auto& nb : nodes_[curr].neighbors) {
                if (!visited[nb]) {
                    visited[nb] = true;
                    q.push(nb);
                }
            }
        }
        return static_cast<double>(visited.size()) / nodes_.size();
    }

    size_t node_count() const { return nodes_.size(); }
    size_t link_count() const { return links_.size(); }
};

} // namespace mesh
} // namespace sdacs
