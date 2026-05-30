% Phase 657 — Prolog Airspace Rules v2 (situation-aware adaptive rules)
:- module(airspace_rules, [can_fly/3, resolve_conflict/4]).

% Altitude zones
altitude_zone(Z, ground) :- Z < 0.
altitude_zone(Z, low) :- Z >= 0, Z < 50.
altitude_zone(Z, medium) :- Z >= 50, Z < 120.
altitude_zone(Z, high) :- Z >= 120.

% Weather constraints
weather_constraint(wind_speed, W, ok) :- W < 10.
weather_constraint(wind_speed, W, warn) :- W >= 10, W < 15.
weather_constraint(wind_speed, W, no_fly) :- W >= 15.

% Can fly predicate
can_fly(drone(_, Z, _), weather(Wind), ok) :-
    altitude_zone(Z, Zone),
    Zone \= ground,
    weather_constraint(wind_speed, Wind, ok).
can_fly(_, weather(Wind), no_fly) :-
    weather_constraint(wind_speed, Wind, no_fly).
can_fly(_, _, warn).

% Conflict resolution
resolve_conflict(drone(Id1, Z1, _), drone(Id2, Z2, _), _, advisory(Id1, descend)) :-
    Z1 > Z2.
resolve_conflict(drone(Id1, _, _), drone(Id2, _, _), _, advisory(Id2, descend)).
