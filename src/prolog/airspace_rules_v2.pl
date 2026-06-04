% Phase 647: Airspace Rules v2 — Prolog
% SDACS enhanced airspace rule engine with dynamic airspace updates

:- module(airspace_rules_v2, [
    zone_class/2,
    conflict_detected/3,
    priority_order/2,
    geofence_check/3,
    can_operate/2,
    resolve/3
]).

% Zone classification
zone_class(zone_a, class_a).
zone_class(zone_b, class_b).
zone_class(zone_c, class_c).
zone_class(zone_g, class_g).

% Conflict detection between two drones
conflict_detected(D1, D2, horizontal) :-
    drone_pos(D1, X1, Y1, _),
    drone_pos(D2, X2, Y2, _),
    D1 \= D2,
    Dx is X1 - X2, Dy is Y1 - Y2,
    Dist is sqrt(Dx*Dx + Dy*Dy),
    Dist < 30.0.

conflict_detected(D1, D2, vertical) :-
    drone_pos(D1, _, _, Z1),
    drone_pos(D2, _, _, Z2),
    D1 \= D2,
    AltDiff is abs(Z1 - Z2),
    AltDiff < 10.0.

% Priority order for conflict resolution
priority_order(emergency, 1).
priority_order(medical,   2).
priority_order(commercial,3).
priority_order(delivery,  4).
priority_order(survey,    5).
priority_order(recreational, 6).

% Geofence boundary check
geofence_check(Drone, Zone, inside) :-
    drone_pos(Drone, X, Y, _),
    zone_boundary(Zone, Cx, Cy, R),
    Dx is X - Cx, Dy is Y - Cy,
    Dist is sqrt(Dx*Dx + Dy*Dy),
    Dist =< R.

geofence_check(Drone, Zone, outside) :-
    \+ geofence_check(Drone, Zone, inside).

% Operational permission
can_operate(Drone, Zone) :-
    drone_class(Drone, Class),
    zone_class(Zone, ZClass),
    class_zone_allowed(Class, ZClass).

class_zone_allowed(commercial,    class_a).
class_zone_allowed(commercial,    class_b).
class_zone_allowed(commercial,    class_c).
class_zone_allowed(commercial,    class_g).
class_zone_allowed(recreational,  class_g).
class_zone_allowed(emergency,     _).

% Conflict resolution
resolve(D1, D2, yield(D2)) :-
    drone_class(D1, C1), drone_class(D2, C2),
    priority_order(C1, P1), priority_order(C2, P2),
    P1 < P2.

resolve(D1, D2, yield(D1)) :-
    drone_class(D1, C1), drone_class(D2, C2),
    priority_order(C1, P1), priority_order(C2, P2),
    P2 < P1.

resolve(_, _, negotiate) :- true.

% Runtime stubs
drone_pos(_, 0, 0, 60) :- fail.
drone_class(_, recreational) :- fail.
zone_boundary(_, 0, 0, 1000) :- fail.
