% Phase 573: Airspace Rules — 공역 규칙 Prolog 추론 엔진
% Rule-based airspace conflict detection and resolution for SDACS.

:- module(airspace_rules, [
    airspace_class/2,
    conflict/3,
    priority/2,
    geofence/2,
    resolve/3
]).

% ── Airspace class definitions ────────────────────────────────────
% airspace_class(Zone, Class)
airspace_class(alpha_sector,    a).
airspace_class(bravo_terminal,  b).
airspace_class(charlie_approach, c).
airspace_class(delta_tower,     d).
airspace_class(echo_airspace,   e).
airspace_class(golf_uncontrolled, g).
airspace_class(restricted_r1,   a).
airspace_class(warning_w2,      b).

% ── Conflict detection ─────────────────────────────────────────────
% conflict(Drone1, Drone2, ConflictType)
conflict(D1, D2, lateral_conflict) :-
    drone_altitude(D1, Z1),
    drone_altitude(D2, Z2),
    abs(Z1 - Z2) < 30,
    drone_position(D1, X1, Y1),
    drone_position(D2, X2, Y2),
    lateral_dist(X1, Y1, X2, Y2, Dist),
    Dist < 100,
    D1 \= D2.

conflict(D, _, geofence_breach) :-
    drone_position(D, X, Y),
    geofence(Zone, rect(Xmin, Xmax, Ymin, Ymax)),
    X >= Xmin, X =< Xmax,
    Y >= Ymin, Y =< Ymax,
    airspace_class(Zone, a).

% ── Priority rules ─────────────────────────────────────────────────
% priority(DroneCategory, Level)
priority(emergency,    10).
priority(medical,       9).
priority(law_enforce,   8).
priority(commercial,    5).
priority(hobbyist,      2).
priority(test,          1).

% ── Geofence definitions ──────────────────────────────────────────
% geofence(Zone, rect(Xmin, Xmax, Ymin, Ymax))
geofence(airport,      rect(0, 5000, 0, 5000)).
geofence(nuclear,      rect(10000, 12000, 10000, 12000)).
geofence(prison,       rect(3000, 3500, 3000, 3500)).
geofence(government,   rect(1000, 1200, 1000, 1200)).

% ── Conflict resolution ────────────────────────────────────────────
% resolve(Drone1, Drone2, Action)
resolve(D1, D2, yield(D2)) :-
    drone_category(D1, Cat1),
    drone_category(D2, Cat2),
    priority(Cat1, P1),
    priority(Cat2, P2),
    P1 > P2, !.
resolve(D1, D2, yield(D1)) :-
    drone_category(D1, Cat1),
    drone_category(D2, Cat2),
    priority(Cat1, P1),
    priority(Cat2, P2),
    P2 > P1, !.
resolve(D1, D2, altitude_deconflict(D1, D2)).

% ── Helper predicates ─────────────────────────────────────────────
lateral_dist(X1, Y1, X2, Y2, Dist) :-
    DX is X1 - X2,
    DY is Y1 - Y2,
    Dist is sqrt(DX*DX + DY*DY).

in_geofence(X, Y) :-
    geofence(_, rect(Xmin, Xmax, Ymin, Ymax)),
    X >= Xmin, X =< Xmax,
    Y >= Ymin, Y =< Ymax.

safe_zone(X, Y) :- \+ in_geofence(X, Y).

% ── Dynamic predicates (asserted at runtime) ─────────────────────
:- dynamic drone_position/3.   % drone_position(ID, X, Y)
:- dynamic drone_altitude/2.   % drone_altitude(ID, Z)
:- dynamic drone_category/2.   % drone_category(ID, Cat)

% Phase marker
phase_id(573).
