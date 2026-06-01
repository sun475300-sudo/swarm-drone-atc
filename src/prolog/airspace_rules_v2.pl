% Airspace rules v2 — Prolog stub for SDACS constraint reasoning
:- module(airspace_rules_v2, [safe_altitude/2, conflict/3, priority/2]).

% Minimum safe altitude rules
safe_altitude(Drone, Alt) :-
    drone_class(Drone, Class),
    min_altitude(Class, MinAlt),
    Alt >= MinAlt.

min_altitude(micro, 30).
min_altitude(small, 50).
min_altitude(medium, 100).

% Conflict detection
conflict(D1, D2, Time) :-
    drone_position(D1, Time, X1, Y1, Z1),
    drone_position(D2, Time, X2, Y2, Z2),
    separation(X1, Y1, Z1, X2, Y2, Z2, Sep),
    Sep < 50.

separation(X1, Y1, Z1, X2, Y2, Z2, Sep) :-
    Sep is sqrt((X2-X1)^2 + (Y2-Y1)^2 + (Z2-Z1)^2).

% Priority ordering
priority(emergency, 0).
priority(atc_directed, 1).
priority(normal, 2).
