% P657: Airspace Rules v2 - Prolog stub
% Declarative airspace safety rule engine

:- module(airspace_rules_v2, [
    safe_altitude/2,
    safe_separation/3,
    conflict_free/2,
    safe_operation/1
]).

% Altitude bounds
min_altitude(30.0).
max_altitude(150.0).

% Minimum horizontal separation (meters)
min_separation(5.0).

% Battery threshold for safe operation
min_battery(0.15).

% Maximum speed (m/s)
max_speed(20.0).

% Check altitude is within bounds
safe_altitude(DroneId, Altitude) :-
    min_altitude(Min),
    max_altitude(Max),
    Altitude >= Min,
    Altitude =< Max,
    format("Drone ~w altitude ~w m: OK~n", [DroneId, Altitude]).

% Calculate 3D distance
distance3d(pos(X1,Y1,Z1), pos(X2,Y2,Z2), Dist) :-
    Dist is sqrt((X2-X1)^2 + (Y2-Y1)^2 + (Z2-Z1)^2).

% Check separation between two drones
safe_separation(DroneA, DroneB, Dist) :-
    min_separation(MinSep),
    Dist >= MinSep,
    format("~w <-> ~w separation ~w m: OK~n", [DroneA, DroneB, Dist]).

% Check no conflicts in a list of drones
conflict_free([], _).
conflict_free([drone(Id, Pos)|Rest], AllDrones) :-
    \+ (member(drone(OtherId, OtherPos), AllDrones),
        OtherId \= Id,
        distance3d(Pos, OtherPos, Dist),
        min_separation(MinSep),
        Dist < MinSep),
    conflict_free(Rest, AllDrones).

% Overall safe operation check
safe_operation(drone(Id, pos(_,_,Z), Battery, Speed)) :-
    safe_altitude(Id, Z),
    min_battery(MinBatt),
    Battery >= MinBatt,
    max_speed(MaxSpd),
    Speed =< MaxSpd.
