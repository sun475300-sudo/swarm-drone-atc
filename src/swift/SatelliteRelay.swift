// Phase 529: Swift Satellite Relay — LEO Orbital Mechanics
import Foundation

struct Vec3 {
    var x, y, z: Double
    static func +(a: Vec3, b: Vec3) -> Vec3 { Vec3(x: a.x+b.x, y: a.y+b.y, z: a.z+b.z) }
    static func *(a: Vec3, s: Double) -> Vec3 { Vec3(x: a.x*s, y: a.y*s, z: a.z*s) }
    var norm: Double { sqrt(x*x + y*y + z*z) }
}

struct Satellite {
    let id: String
    var position: Vec3
    var velocity: Vec3
    let altitudeKm: Double
    let bandwidthMbps: Double
    let latencyMs: Double
}

struct RelayLink {
    let droneId: String
    var satId: String
    var snrDb: Double
    var throughputMbps: Double
    var handovers: Int
}

class PRNG {
    var state: UInt64
    init(_ seed: UInt64) { self.state = seed ^ 0x6c62272e07bb0142 }
    func next() -> UInt64 {
        state ^= state << 13; state ^= state >> 7; state ^= state << 17
        return state
    }
    func uniform() -> Double { Double(next() & 0x7FFFFFFF) / Double(0x7FFFFFFF) }
    func normal() -> Double {
        let u1 = max(uniform(), 1e-10), u2 = uniform()
        return sqrt(-2 * log(u1)) * cos(2 * .pi * u2)
    }
}

func createConstellation(nSats: Int, altKm: Double, rng: PRNG) -> [Satellite] {
    let earthR = 6371.0
    let mu = 398600.4418
    let r = earthR + altKm
    let vCirc = sqrt(mu / r)

    return (0..<nSats).map { i in
        let angle = 2.0 * .pi * Double(i) / Double(nSats) + rng.normal() * 0.1
        let incl = (50.0 + rng.uniform() * 48.0) * .pi / 180.0
        let pos = Vec3(x: r * cos(angle), y: r * sin(angle) * cos(incl), z: r * sin(angle) * sin(incl))
        let vel = Vec3(x: -vCirc * sin(angle), y: vCirc * cos(angle) * cos(incl), z: vCirc * cos(angle) * sin(incl))
        let lat = vCirc / r * 1000 * 2
        return Satellite(id: String(format: "SAT-%03d", i), position: pos, velocity: vel,
                        altitudeKm: altKm, bandwidthMbps: 50 + rng.uniform() * 150,
                        latencyMs: lat)
    }
}

func propagate(_ sat: inout Satellite, dtS: Double) {
    sat.position = sat.position + sat.velocity * (dtS / 1000.0)
    let r = sat.position.norm
    if r > 0 {
        let targetR = 6371.0 + sat.altitudeKm
        sat.position = sat.position * (targetR / r)
    }
}

func selectBestSat(dronePos: Vec3, satellites: [Satellite]) -> Satellite? {
    var best: Satellite? = nil
    var bestScore = -1.0
    for sat in satellites {
        let dist = (sat.position + dronePos * -1.0).norm
        if dist > sat.altitudeKm * 3 { continue }
        let elev = asin(sat.altitudeKm / (dist + 1e-8)) * 180.0 / .pi
        if elev < 10 { continue }
        let score = elev / 90.0 * sat.bandwidthMbps / 200.0
        if score > bestScore { bestScore = score; best = sat }
    }
    return best
}

// Main
let rng = PRNG(42)
var sats = createConstellation(nSats: 12, altKm: 550, rng: rng)
var links: [RelayLink] = []
let nDrones = 10

for i in 0..<nDrones {
    let dronePos = Vec3(x: 6371 + rng.normal() * 0.001, y: rng.normal() * 0.001, z: 0.05 + rng.uniform() * 0.1)
    if let best = selectBestSat(dronePos: dronePos, satellites: sats) {
        let snr = 10.0 + rng.uniform() * 20.0
        links.append(RelayLink(droneId: "drone_\(i)", satId: best.id,
                               snrDb: snr, throughputMbps: best.bandwidthMbps * snr / 30.0, handovers: 0))
    }
}

var totalHandovers = 0
for _ in 0..<20 {
    for idx in sats.indices { propagate(&sats[idx], dtS: 10) }
    for idx in links.indices {
        if rng.uniform() < 0.05 {
            let dp = Vec3(x: 6371, y: 0, z: 0.1)
            if let best = selectBestSat(dronePos: dp, satellites: sats), best.id != links[idx].satId {
                links[idx].satId = best.id
                links[idx].handovers += 1
                totalHandovers += 1
            }
        }
    }
}

print("Satellites: \(sats.count)")
print("Active links: \(links.count)")
print("Total handovers: \(totalHandovers)")
let avgLat = links.isEmpty ? 0 : links.map { $0.snrDb }.reduce(0, +) / Double(links.count)
print(String(format: "Avg SNR: %.1f dB", avgLat))
