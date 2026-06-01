% Airspace Rules — Prolog knowledge base for SDACS conflict resolution
% Phase 573

:- module(airspace_rules, [
    airspace_class/2,
    conflict/3,
    priority/2,
    geofence/2,
    resolve_conflict/4
]).

% ── Airspace Class Definitions ───────────────────────────────────
% airspace_class(ID, Class) — maps airspace zone to ICAO class

airspace_class(zone_a, class_a).
airspace_class(zone_b, class_b).
airspace_class(zone_c, class_c).
airspace_class(zone_d, class_d).
airspace_class(restricted_01, restricted).
airspace_class(tma_seoul, class_d).
airspace_class(ctr_gimpo, class_d).

% ── Conflict Detection Rules ─────────────────────────────────────
% conflict(Drone1, Drone2, Type)

conflict(D1, D2, separation_violation) :-
    drone_position(D1, X1, Y1, Z1),
    drone_position(D2, X2, Y2, Z2),
    horizontal_sep(X1, Y1, X2, Y2, HSep),
    vertical_sep(Z1, Z2, VSep),
    HSep < 50.0,
    VSep < 30.0,
    D1 \= D2.

conflict(D1, _, nfz_violation) :-
    drone_position(D1, X, Y, _),
    geofence(nfz, boundary(X, Y)).

horizontal_sep(X1, Y1, X2, Y2, Sep) :-
    Sep is sqrt((X2-X1)^2 + (Y2-Y1)^2).

vertical_sep(Z1, Z2, Sep) :-
    Sep is abs(Z2 - Z1).

% ── Priority Rules ───────────────────────────────────────────────
% priority(FlightType, Level) — lower number = higher priority

priority(emergency, 0).
priority(search_and_rescue, 1).
priority(medical, 2).
priority(atc_directed, 3).
priority(commercial, 4).
priority(normal, 5).
priority(recreational, 6).

% ── Geofence Rules ───────────────────────────────────────────────
% geofence(ZoneID, Constraint)

geofence(nfz_airport_1, radius(37.5583, 126.7906, 9260)).
geofence(nfz_military_1, polygon([p(37.4, 126.8), p(37.5, 126.9), p(37.4, 127.0)])).
geofence(restricted_airspace, altitude_ceiling(300)).

% ── Conflict Resolution ──────────────────────────────────────────
% resolve_conflict(+Drone1, +Drone2, +ConflictType, -Resolution)

resolve_conflict(D1, D2, separation_violation, advisory(D1, ascend, 50)) :-
    priority(D1, P1),
    priority(D2, P2),
    P1 > P2, !.

resolve_conflict(D1, D2, separation_violation, advisory(D2, descend, 50)) :-
    priority(D1, P1),
    priority(D2, P2),
    P1 =< P2, !.

resolve_conflict(D1, _, nfz_violation, advisory(D1, return_to_launch, 0)).
