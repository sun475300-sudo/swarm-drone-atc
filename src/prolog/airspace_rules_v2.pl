% Phase 657 — Airspace Rules v2 in Prolog (context-aware adaptive)
:- module(airspace_rules, [safe_to_fly/2, conflict/3, resolve/3]).

% Minimum separation rules (meters)
min_separation(vfr, 30).
min_separation(ifr, 100).
min_separation(urban, 50).
min_separation(rural, 20).

% A drone is safe to fly if altitude and separation are within limits
safe_to_fly(Drone, Context) :-
    drone(Drone, Alt, _),
    max_altitude(Context, MaxAlt),
    Alt =< MaxAlt,
    \+ separation_violation(Drone, Context).

separation_violation(Drone, Context) :-
    drone(Drone, _, Pos),
    drone(Other, _, OtherPos),
    Drone \= Other,
    distance(Pos, OtherPos, D),
    min_separation(Context, MinSep),
    D < MinSep.

conflict(D1, D2, Distance) :-
    drone(D1, _, P1), drone(D2, _, P2),
    D1 @< D2, distance(P1, P2, Distance).

resolve(D1, D2, altitude_change) :-
    conflict(D1, D2, _), !.
resolve(_, _, heading_change).

distance(p(X1,Y1,Z1), p(X2,Y2,Z2), D) :-
    D is sqrt((X1-X2)^2 + (Y1-Y2)^2 + (Z1-Z2)^2).

max_altitude(urban, 120).
max_altitude(rural, 400).
max_altitude(vfr, 1000).
