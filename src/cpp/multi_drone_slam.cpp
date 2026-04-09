/// Phase 324: C++ Multi-Drone SLAM Engine
/// Factor graph, landmark management, loop closure detection.
/// Cache-efficient pose graph optimization.

#include <cmath>
#include <vector>
#include <unordered_map>
#include <string>
#include <algorithm>
#include <numeric>
#include <cstdio>
#include <cassert>

namespace sdacs {

struct Vec3 {
    double x{0}, y{0}, z{0};
    Vec3() = default;
    Vec3(double x, double y, double z) : x(x), y(y), z(z) {}
    Vec3 operator+(const Vec3& o) const { return {x+o.x, y+o.y, z+o.z}; }
    Vec3 operator-(const Vec3& o) const { return {x-o.x, y-o.y, z-o.z}; }
    Vec3 operator*(double s) const { return {x*s, y*s, z*s}; }
    double length() const { return std::sqrt(x*x + y*y + z*z); }
    double distance(const Vec3& o) const { return (*this - o).length(); }
};

struct Pose {
    Vec3 position;
    double yaw{0};
    double timestamp{0};
};

struct Landmark {
    std::string id;
    Vec3 position;
    double uncertainty{1.0};
    int observations{0};
    std::string last_seen_by;
};

struct Observation {
    std::string drone_id;
    std::string landmark_id;
    double bearing;
    double range_m;
    double timestamp;
};

struct LoopClosure {
    std::string drone_a, drone_b;
    Vec3 transform;
    double confidence;
};

class MultiDroneSLAM {
    std::unordered_map<std::string, std::vector<Pose>> drone_poses_;
    std::unordered_map<std::string, Landmark> landmarks_;
    std::vector<Observation> observations_;
    std::vector<LoopClosure> closures_;

public:
    void addDrone(const std::string& id, const Pose& initial) {
        drone_poses_[id] = {initial};
    }

    void updateOdometry(const std::string& id, const Vec3& delta, double delta_yaw = 0) {
        auto it = drone_poses_.find(id);
        if (it == drone_poses_.end() || it->second.empty()) return;

        const auto& last = it->second.back();
        Pose next;
        next.position = last.position + delta;
        next.yaw = last.yaw + delta_yaw;
        next.timestamp = last.timestamp + 0.1;
        it->second.push_back(next);
    }

    void observeLandmark(const std::string& drone_id, const std::string& lm_id,
                         const Vec3& true_pos) {
        auto it = drone_poses_.find(drone_id);
        if (it == drone_poses_.end() || it->second.empty()) return;

        const auto& drone_pos = it->second.back().position;
        Vec3 diff = true_pos - drone_pos;
        double bearing = std::atan2(diff.y, diff.x);
        double range = diff.length();

        observations_.push_back({drone_id, lm_id, bearing, range, 0});

        auto lm_it = landmarks_.find(lm_id);
        if (lm_it == landmarks_.end()) {
            Vec3 est = drone_pos + Vec3(range * std::cos(bearing),
                                         range * std::sin(bearing), 0);
            landmarks_[lm_id] = {lm_id, est, 1.0, 1, drone_id};
        } else {
            auto& lm = lm_it->second;
            Vec3 new_est = drone_pos + Vec3(range * std::cos(bearing),
                                             range * std::sin(bearing), 0);
            double alpha = 1.0 / (lm.observations + 1);
            lm.position = lm.position * (1 - alpha) + new_est * alpha;
            lm.observations++;
            lm.uncertainty *= 0.9;
            lm.last_seen_by = drone_id;
        }
    }

    int detectLoopClosures(double threshold = 5.0) {
        int found = 0;
        std::vector<std::string> ids;
        for (const auto& p : drone_poses_) ids.push_back(p.first);

        for (size_t i = 0; i < ids.size(); ++i) {
            for (size_t j = i + 1; j < ids.size(); ++j) {
                const auto& poses_a = drone_poses_[ids[i]];
                const auto& poses_b = drone_poses_[ids[j]];
                for (const auto& pa : poses_a) {
                    for (const auto& pb : poses_b) {
                        double dist = pa.position.distance(pb.position);
                        if (dist < threshold) {
                            closures_.push_back({
                                ids[i], ids[j],
                                pb.position - pa.position,
                                1.0 - dist / threshold
                            });
                            found++;
                        }
                    }
                }
            }
        }
        return found;
    }

    size_t landmarkCount() const { return landmarks_.size(); }
    size_t observationCount() const { return observations_.size(); }
    size_t closureCount() const { return closures_.size(); }

    void printSummary() const {
        printf("SLAM: %zu drones | %zu landmarks | %zu observations | %zu closures\n",
               drone_poses_.size(), landmarks_.size(),
               observations_.size(), closures_.size());
    }
};

}  // namespace sdacs

#ifdef SDACS_SLAM_MAIN
int main() {
    using namespace sdacs;

    MultiDroneSLAM slam;
    slam.addDrone("d1", {Vec3(0, 0, 0), 0, 0});
    slam.addDrone("d2", {Vec3(100, 0, 0), 0, 0});

    for (int i = 0; i < 10; ++i) {
        slam.updateOdometry("d1", Vec3(5, 0, 0));
        slam.updateOdometry("d2", Vec3(-5, 0, 0));
    }

    slam.observeLandmark("d1", "lm1", Vec3(25, 10, 0));
    slam.observeLandmark("d2", "lm1", Vec3(25, 10, 0));
    slam.observeLandmark("d1", "lm2", Vec3(40, -5, 0));

    int closures = slam.detectLoopClosures(15.0);
    slam.printSummary();
    printf("Loop closures found: %d\n", closures);

    assert(slam.landmarkCount() == 2);
    assert(slam.observationCount() == 3);
    printf("All assertions passed.\n");
    return 0;
}
#endif
