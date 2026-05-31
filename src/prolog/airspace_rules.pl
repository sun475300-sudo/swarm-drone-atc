% airspace_rules.pl - Airspace management rules for SDACS
% Prolog knowledge base for drone airspace control

:- module(airspace_rules, [
    airspace_class/2,
    conflict/3,
    priority/2,
    geofence/3,
    safe_altitude/2,
    resolve_conflict/3
]).

% Airspace class definitions
airspace_class(class_a, above_18000_ft).
airspace_class(class_b, major_airport).
airspace_class(class_c, regional_airport).
airspace_class(class_d, small_airport).
airspace_class(class_e, general_aviation).
airspace_class(class_g, uncontrolled).
airspace_class(sua, special_use).

% Priority rules for different drone types
priority(emergency, 1).
priority(medical, 2).
priority(law_enforcement, 3).
priority(commercial, 4).
priority(recreational, 5).

% Conflict detection between two drones
conflict(DroneA, DroneB, Reason) :-
    drone_position(DroneA, PosA),
    drone_position(DroneB, PosB),
    separation_distance(PosA, PosB, D),
    minimum_separation(MinSep),
    D < MinSep,
    Reason = separation_violation.

conflict(DroneA, DroneB, altitude_conflict) :-
    drone_altitude(DroneA, AltA),
    drone_altitude(DroneB, AltB),
    abs(AltA - AltB) < 50,
    drone_horizontal_close(DroneA, DroneB).

% Geofence definitions
geofence(airport_zone, circular, [lat(37.5665), lon(126.9780), radius(5000)]).
geofence(restricted_zone, polygon, [military_base]).
geofence(no_fly_zone, circular, [lat(37.5172), lon(127.0473), radius(2000)]).

geofence_violation(DroneID, Zone) :-
    drone_position(DroneID, Pos),
    geofence(Zone, circular, [lat(ZLat), lon(ZLon), radius(R)]),
    haversine_distance(Pos, point(ZLat, ZLon), D),
    D < R.

% Safe altitude rules
safe_altitude(urban_area, 120).
safe_altitude(rural_area, 400).
safe_altitude(over_people, 30).
safe_altitude(restricted, 0).

% Conflict resolution
resolve_conflict(DroneA, DroneB, Resolution) :-
    priority(TypeA, PA),
    priority(TypeB, PB),
    drone_type(DroneA, TypeA),
    drone_type(DroneB, TypeB),
    PA < PB,
    Resolution = yield(DroneB, DroneA).

resolve_conflict(DroneA, DroneB, altitude_separation(DroneA, DroneB)) :-
    conflict(DroneA, DroneB, altitude_conflict),
    adjust_altitude(DroneA, DroneB).

% Helper predicates
minimum_separation(30.0).
separation_distance(point(X1,Y1,Z1), point(X2,Y2,Z2), D) :-
    D is sqrt((X2-X1)^2 + (Y2-Y1)^2 + (Z2-Z1)^2).

drone_horizontal_close(A, B) :-
    drone_position(A, point(X1,Y1,_)),
    drone_position(B, point(X2,Y2,_)),
    D is sqrt((X2-X1)^2 + (Y2-Y1)^2),
    D < 100.
