// Phase 499: Urban Air Mobility (Swift)
// 도심항공교통, 버티포트 네트워크, Protocol-Oriented 설계

import Foundation

// MARK: - Types

enum VehicleType: String, CaseIterable {
    case evtol = "eVTOL"
    case droneCargo = "drone_cargo"
    case airTaxi = "air_taxi"
    case emergency = "emergency"
}

enum VertiportStatus: String {
    case open, busy, closed, maintenance
}

struct Coordinate {
    let lat: Double
    let lon: Double
    let alt: Double

    func distanceTo(_ other: Coordinate) -> Double {
        let dlat = (other.lat - lat) * 111000
        let dlon = (other.lon - lon) * 111000 * cos(lat * .pi / 180)
        let dalt = other.alt - alt
        return sqrt(dlat * dlat + dlon * dlon + dalt * dalt)
    }
}

// MARK: - Protocols

protocol Schedulable {
    var id: String { get }
    var departureTime: Double { get }
    var arrivalTime: Double { get }
    var status: String { get set }
}

protocol CapacityManaged {
    var capacity: Int { get }
    var currentLoad: Int { get set }
    var utilization: Double { get }
}

// MARK: - Models

struct Vertiport: CapacityManaged {
    let portId: String
    let position: Coordinate
    let capacity: Int
    var currentLoad: Int = 0
    var status: VertiportStatus = .open
    let chargeRateKW: Double = 150.0
    let landingPads: Int

    var utilization: Double {
        Double(currentLoad) / Double(max(capacity, 1))
    }

    var availablePads: Int {
        max(0, landingPads - currentLoad)
    }
}

struct UAMFlight: Schedulable {
    let id: String
    let vehicleType: VehicleType
    let origin: String
    let destination: String
    let departureTime: Double
    var arrivalTime: Double
    var passengers: Int = 0
    var cargoKg: Double = 0
    var status: String = "scheduled"
    var energyKWh: Double = 0
}

struct Corridor {
    let origin: String
    let destination: String
    let altitudeM: Double
    let widthM: Double
    let distanceM: Double
    let flightTimeMin: Double
}

struct DemandForecast {
    let hour: Int
    let origin: String
    let destination: String
    let predictedDemand: Double
    let confidence: Double
}

// MARK: - PRNG

struct PRNG {
    private var state: UInt64

    init(seed: UInt64) {
        state = seed &+ 1
    }

    mutating func next() -> Double {
        state ^= state << 13
        state ^= state >> 7
        state ^= state << 17
        return Double(state) / Double(UInt64.max)
    }

    mutating func gaussian(mean: Double = 0, std: Double = 1) -> Double {
        let u1 = max(next(), 1e-10)
        let u2 = next()
        return mean + std * sqrt(-2 * log(u1)) * cos(2 * .pi * u2)
    }
}

// MARK: - UAM Manager

class UrbanAirMobilityManager {
    private(set) var vertiports: [String: Vertiport] = [:]
    private(set) var flights: [UAMFlight] = []
    private(set) var corridors: [String: Corridor] = [:]
    private var rng: PRNG
    private var time: Double = 0
    private var flightCounter = 0

    init(seed: UInt64 = 42) {
        rng = PRNG(seed: seed)
    }

    @discardableResult
    func addVertiport(id: String, lat: Double, lon: Double, alt: Double = 0,
                      capacity: Int = 4, pads: Int = 2) -> Vertiport {
        let vp = Vertiport(portId: id, position: Coordinate(lat: lat, lon: lon, alt: alt),
                          capacity: capacity, landingPads: pads)
        vertiports[id] = vp
        return vp
    }

    @discardableResult
    func createCorridor(origin: String, destination: String,
                       altitude: Double = 300, width: Double = 100) -> Corridor? {
        guard let o = vertiports[origin], let d = vertiports[destination] else { return nil }
        let dist = o.position.distanceTo(d.position)
        let flightTime = dist / 200.0 * 60.0 / 1000.0  // ~200 km/h
        let corridor = Corridor(origin: origin, destination: destination,
                               altitudeM: altitude, widthM: width,
                               distanceM: dist, flightTimeMin: flightTime)
        corridors["\(origin)->\(destination)"] = corridor
        corridors["\(destination)->\(origin)"] = Corridor(
            origin: destination, destination: origin,
            altitudeM: altitude, widthM: width,
            distanceM: dist, flightTimeMin: flightTime)
        return corridor
    }

    func scheduleFlight(origin: String, destination: String,
                       vehicle: VehicleType = .airTaxi,
                       passengers: Int = 2) -> UAMFlight? {
        guard let op = vertiports[origin], let _ = vertiports[destination],
              op.status != .closed else { return nil }

        flightCounter += 1
        let key = "\(origin)->\(destination)"
        let flightTime = corridors[key]?.flightTimeMin ?? 15.0

        var flight = UAMFlight(
            id: String(format: "UAM-%05d", flightCounter),
            vehicleType: vehicle, origin: origin, destination: destination,
            departureTime: time, arrivalTime: time + flightTime * 60,
            passengers: passengers, energyKWh: flightTime * 2.5)
        flights.append(flight)
        vertiports[origin]?.currentLoad += 1
        return flight
    }

    func tick(dt: Double = 60) -> (departed: Int, arrived: Int) {
        time += dt
        var departed = 0, arrived = 0

        for i in flights.indices {
            if flights[i].status == "scheduled" && time >= flights[i].departureTime {
                flights[i].status = "airborne"
                departed += 1
            } else if flights[i].status == "airborne" && time >= flights[i].arrivalTime {
                flights[i].status = "arrived"
                arrived += 1
                vertiports[flights[i].origin]?.currentLoad -= 1
                vertiports[flights[i].destination]?.currentLoad += 1
            }
        }
        return (departed, arrived)
    }

    func forecastDemand(route: String, hour: Int) -> DemandForecast {
        var base = 10.0 + 15.0 * sin(.pi * Double(hour) / 12.0)
        if (7...9).contains(hour) || (17...19).contains(hour) { base *= 1.5 }
        var r = rng
        let noise = r.gaussian() * 3
        rng = r

        let parts = route.split(separator: "-").map(String.init)
        return DemandForecast(
            hour: hour, origin: parts.first ?? route,
            destination: parts.last ?? route,
            predictedDemand: max(0, base + noise),
            confidence: 0.7 + Double.random(in: 0...0.25))
    }

    var networkStatus: [String: Any] {
        [
            "vertiports": vertiports.count,
            "corridors": corridors.count / 2,
            "total_flights": flights.count,
            "airborne": flights.filter { $0.status == "airborne" }.count,
            "completed": flights.filter { $0.status == "arrived" }.count,
            "total_passengers": flights.reduce(0) { $0 + $1.passengers },
            "avg_utilization": vertiports.values.isEmpty ? 0 :
                vertiports.values.reduce(0.0) { $0 + $1.utilization } / Double(vertiports.count)
        ]
    }
}
