% Phase 573: Airspace Rules — Prolog Logic Engine
% SDACS declarative airspace classification and conflict resolution

:- module(airspace_rules, [
    airspace_class/3,
    conflict/4,
    priority/2,
    geofence/3,
    resolve_conflict/4,
    can_enter/2,
    altitude_range/3
]).

% Airspace classification rules
airspace_class(Zone, class_a, Params) :-
    zone_altitude(Zone, Alt),
    Alt >= 18000,
    Params = [controlled, ifr_only, clearance_required].

airspace_class(Zone, class_b, Params) :-
    zone_altitude(Zone, Alt),
    Alt >= 1200, Alt < 18000,
    zone_type(Zone, terminal),
    Params = [controlled, atc_clearance, transponder_required].

airspace_class(Zone, class_c, Params) :-
    zone_altitude(Zone, Alt),
    Alt >= 1200, Alt < 4000,
    zone_type(Zone, approach),
    Params = [controlled, two_way_radio, transponder].

airspace_class(Zone, class_d, Params) :-
    zone_type(Zone, tower_controlled),
    Params = [controlled, two_way_radio].

airspace_class(Zone, class_e, Params) :-
    zone_type(Zone, controlled_en_route),
    Params = [controlled, ifr_separation].

airspace_class(Zone, class_g, Params) :-
    zone_type(Zone, uncontrolled),
    Params = [uncontrolled, vfr_allowed].

% Geofence definition and enforcement
geofence(DroneId, Zone, Status) :-
    drone_position(DroneId, Pos),
    zone_boundary(Zone, Boundary),
    ( inside_boundary(Pos, Boundary) ->
        Status = inside
    ;
        Status = outside
    ).

geofence(DroneId, restricted_zone, violation) :-
    drone_position(DroneId, Pos),
    restricted_area(Area),
    inside_boundary(Pos, Area).

% Conflict detection between drones
conflict(Drone1, Drone2, Type, Severity) :-
    drone_position(Drone1, Pos1),
    drone_position(Drone2, Pos2),
    separation_distance(Pos1, Pos2, Dist),
    minimum_separation(MinSep),
    Dist < MinSep,
    conflict_type(Drone1, Drone2, Type),
    severity_level(Dist, MinSep, Severity).

conflict_type(D1, D2, head_on) :-
    drone_heading(D1, H1),
    drone_heading(D2, H2),
    angle_between(H1, H2, Angle),
    Angle > 150.

conflict_type(D1, D2, converging) :-
    drone_heading(D1, H1),
    drone_heading(D2, H2),
    angle_between(H1, H2, Angle),
    Angle >= 30, Angle =< 150.

conflict_type(_, _, overtake) :- true.

% Priority rules for conflict resolution
priority(Drone, Priority) :-
    drone_class(Drone, Class),
    class_priority(Class, Priority).

class_priority(emergency, 1).
class_priority(medical, 2).
class_priority(commercial, 3).
class_priority(delivery, 4).
class_priority(recreational, 5).

% Resolve conflict based on priority
resolve_conflict(Drone1, Drone2, Action1, Action2) :-
    priority(Drone1, P1),
    priority(Drone2, P2),
    ( P1 < P2 ->
        Action1 = maintain,
        Action2 = yield
    ; P1 > P2 ->
        Action1 = yield,
        Action2 = maintain
    ;
        Action1 = turn_right,
        Action2 = turn_right
    ).

% Entry permission check
can_enter(DroneId, Zone) :-
    drone_class(DroneId, Class),
    airspace_class(Zone, ZoneClass, _Params),
    class_allowed(Class, ZoneClass).

class_allowed(commercial, class_a).
class_allowed(commercial, class_b).
class_allowed(commercial, class_c).
class_allowed(commercial, class_d).
class_allowed(commercial, class_e).
class_allowed(commercial, class_g).
class_allowed(recreational, class_g).
class_allowed(recreational, class_e).

% Altitude range for zones
altitude_range(class_a, 18000, unlimited).
altitude_range(class_b, 1200, 18000).
altitude_range(class_c, 1200, 4000).
altitude_range(class_g, 0, 1200).

% Helper predicates (stubs — populated at runtime)
inside_boundary(_, _) :- fail.
zone_altitude(_, 0) :- fail.
zone_type(_, unknown) :- fail.
zone_boundary(_, []) :- fail.
restricted_area([]) :- fail.
drone_position(_, [0,0,0]) :- fail.
drone_heading(_, 0) :- fail.
drone_class(_, recreational) :- fail.
separation_distance(_, _, 0) :- fail.
minimum_separation(50).
angle_between(_, _, 0) :- fail.
severity_level(D, M, high) :- D < M / 2, !.
severity_level(_, _, medium).
