% Phase 647: Airspace Rules v2 — 공역 규칙 논리 엔진 (Prolog)
% Extended airspace conflict resolution rules for SDACS.

:- module(airspace_rules_v2, [
    airspace_class/2,
    conflict/3,
    priority/2,
    geofence/2,
    resolve_conflict/3,
    safe_altitude/2,
    separation_required/3
]).

% ── Airspace Class Definitions ──────────────────────────────────
% airspace_class(Zone, Class) — Class A-G classification
airspace_class(restricted_zone_1, a).
airspace_class(controlled_alpha,   b).
airspace_class(terminal_bravo,     c).
airspace_class(approach_charlie,   d).
airspace_class(low_altitude_echo,  e).
airspace_class(general_use,        g).
airspace_class(military_moa,       a).
airspace_class(national_park,      b).

% ── Conflict Detection ───────────────────────────────────────────
% conflict(DroneA, DroneB, Reason) — two drones are in conflict
conflict(D1, D2, separation_violation) :-
    drone_pos(D1, X1, Y1, Z1),
    drone_pos(D2, X2, Y2, Z2),
    D1 \= D2,
    separation_required(Z1, Z2, MinSep),
    Dist is sqrt((X1-X2)^2 + (Y1-Y2)^2 + (Z1-Z2)^2),
    Dist < MinSep.

conflict(D, _, geofence_violation) :-
    drone_pos(D, X, Y, _),
    geofence(Zone, boundary(Xmin, Xmax, Ymin, Ymax)),
    X >= Xmin, X =< Xmax,
    Y >= Ymin, Y =< Ymax,
    airspace_class(Zone, a).

% ── Priority Rules ───────────────────────────────────────────────
% priority(DroneID, Level) — higher level = higher priority
priority(emergency_drone, 10).
priority(medical_drone,    9).
priority(law_enforcement,  8).
priority(commercial,       5).
priority(recreational,     2).
priority(test_drone,       1).

% ── Geofence Definitions ─────────────────────────────────────────
% geofence(Zone, boundary(Xmin, Xmax, Ymin, Ymax))
geofence(airport_zone,    boundary(0, 5000, 0, 5000)).
geofence(nuclear_plant,   boundary(10000, 15000, 10000, 15000)).
geofence(stadium,         boundary(2000, 3000, 2000, 3000)).
geofence(government_bldg, boundary(500, 600, 500, 600)).

% ── Separation Requirements ──────────────────────────────────────
% separation_required(Alt1, Alt2, MinSepMeters)
separation_required(Alt1, Alt2, 30) :-
    Alt1 > 120, Alt2 > 120, !.
separation_required(Alt1, Alt2, 50) :-
    Alt1 > 400, Alt2 > 400, !.
separation_required(_, _, 15).

% ── Safe Altitude ────────────────────────────────────────────────
% safe_altitude(Zone, MinAlt)
safe_altitude(airport_zone,    0).
safe_altitude(restricted_zone_1, 9999).
safe_altitude(general_use,     30).
safe_altitude(low_altitude_echo, 10).

% ── Conflict Resolution ──────────────────────────────────────────
% resolve_conflict(DroneA, DroneB, Action)
resolve_conflict(D1, D2, yield(D2)) :-
    priority(D1, P1),
    priority(D2, P2),
    P1 > P2, !.
resolve_conflict(D1, D2, yield(D1)) :-
    priority(D1, P1),
    priority(D2, P2),
    P2 > P1, !.
resolve_conflict(D1, D2, altitude_split(D1, D2)) :-
    % Equal priority: altitude-based separation
    drone_pos(D1, _, _, Z1),
    drone_pos(D2, _, _, Z2),
    Z1 =\= Z2, !.
resolve_conflict(D1, D2, hold(D1)) :-
    % Fallback: lower-ID drone holds
    D1 @< D2.

% ── Helper: drone position database (runtime asserted) ───────────
% drone_pos(DroneID, X, Y, Z) is asserted dynamically during simulation.

% ── Phase marker ─────────────────────────────────────────────────
phase_marker(647).
