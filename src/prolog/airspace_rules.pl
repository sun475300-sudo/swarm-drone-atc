% SDACS Airspace Rules — Prolog
% Declarative airspace management rules

% Airspace class definitions
airspace_class(class_a, 18000, 60000, ifr_only).
airspace_class(class_b, 0, 10000, clearance_required).
airspace_class(class_c, 0, 4000, atc_communication).
airspace_class(class_d, 0, 2500, atc_communication).
airspace_class(class_e, 1200, 18000, vfr_allowed).
airspace_class(class_g, 0, 1200, uncontrolled).

% Drone priority levels
priority(emergency, 0).
priority(medical, 1).
priority(law_enforcement, 2).
priority(commercial, 3).
priority(recreational, 4).

% Geofence definitions
geofence(airport_exclusion, circle, [0.0, 0.0], 5000).
geofence(hospital_zone,     circle, [100.0, 200.0], 500).
geofence(restricted_area_r1, polygon, [[10,10],[10,20],[20,20],[20,10]], 0).
geofence(urban_corridor,    corridor, [0,0], [100,100], 50).

% Conflict detection rules
conflict(DroneA, DroneB) :-
    drone_position(DroneA, XA, YA, ZA),
    drone_position(DroneB, XB, YB, ZB),
    DroneA \= DroneB,
    separation_distance(XA, YA, ZA, XB, YB, ZB, D),
    minimum_separation(MinSep),
    D < MinSep.

separation_distance(X1, Y1, Z1, X2, Y2, Z2, D) :-
    DX is X2 - X1,
    DY is Y2 - Y1,
    DZ is Z2 - Z1,
    D is sqrt(DX*DX + DY*DY + DZ*DZ).

minimum_separation(50.0).

% Geofence violation check
geofence_violation(Drone, Zone) :-
    drone_position(Drone, X, Y, _),
    geofence(Zone, circle, [CX, CY], Radius),
    DX is X - CX,
    DY is Y - CY,
    Dist is sqrt(DX*DX + DY*DY),
    Dist < Radius.

% Priority-based conflict resolution
resolve_conflict(DroneA, DroneB, Winner) :-
    conflict(DroneA, DroneB),
    drone_priority(DroneA, PA),
    drone_priority(DroneB, PB),
    priority(PA, VA),
    priority(PB, VB),
    (VA < VB -> Winner = DroneA ; Winner = DroneB).

% Altitude band assignment by class
altitude_band(Drone, Class) :-
    drone_position(Drone, _, _, Alt),
    airspace_class(Class, MinAlt, MaxAlt, _),
    Alt >= MinAlt,
    Alt =< MaxAlt.
