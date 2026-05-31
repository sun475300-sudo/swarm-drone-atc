% Phase 573 — Prolog airspace rules
% SDACS airspace class classification, conflict resolution,
% priority ordering, and geofence enforcement predicates.

:- module(airspace_rules, [
    airspace_class/3,
    conflict/4,
    priority/3,
    geofence/4,
    resolve_conflict/4,
    safe_altitude/3,
    allowed_in_class/2
]).

% ---------------------------------------------------------------
% airspace_class(+ID, +Altitude, -Class)
% Classify a point by altitude (metres AGL) into ICAO classes.
% ---------------------------------------------------------------
airspace_class(_ID, Alt, class_g) :-
    Alt >= 0, Alt < 120, !.
airspace_class(_ID, Alt, class_e) :-
    Alt >= 120, Alt < 600, !.
airspace_class(_ID, Alt, class_d) :-
    Alt >= 600, Alt < 1200, !.
airspace_class(_ID, Alt, class_c) :-
    Alt >= 1200, Alt < 3000, !.
airspace_class(_ID, Alt, class_b) :-
    Alt >= 3000, !.

% ---------------------------------------------------------------
% conflict(+Drone1, +Pos1, +Drone2, +Pos2)
% Two drones are in conflict if their 3D separation falls
% below the minimum safe separation distance (30 m).
% Pos = pos(X, Y, Z) in metres.
% ---------------------------------------------------------------
conflict(D1, pos(X1,Y1,Z1), D2, pos(X2,Y2,Z2)) :-
    D1 \= D2,
    DX is X2 - X1, DY is Y2 - Y1, DZ is Z2 - Z1,
    Dist2 is DX*DX + DY*DY + DZ*DZ,
    Dist2 < 900.   % 30^2 = 900

% ---------------------------------------------------------------
% priority(+Class, +DroneType, -Level)
% Higher Level means higher right-of-way priority.
% DroneType: emergency | cargo | recreational | survey
% ---------------------------------------------------------------
priority(_Class, emergency,    100) :- !.
priority(class_b, _Type,        80) :- !.
priority(class_c, cargo,        70) :- !.
priority(class_c, survey,       65) :- !.
priority(_Class,  cargo,        50) :- !.
priority(_Class,  survey,       40) :- !.
priority(_Class,  recreational, 10) :- !.
priority(_Class,  _Unknown,      5).

% ---------------------------------------------------------------
% geofence(+DroneID, +Pos, +Zone, -Status)
% Zone = geofence(CenterX, CenterY, Radius, MaxAlt)
% Status: inside | outside | altitude_violation
% ---------------------------------------------------------------
geofence(_ID, pos(X, Y, Z), geofence(CX, CY, R, MaxAlt), altitude_violation) :-
    Z > MaxAlt,
    DX is X - CX, DY is Y - CY,
    Dist2 is DX*DX + DY*DY,
    Dist2 =< R*R, !.
geofence(_ID, pos(X, Y, _Z), geofence(CX, CY, R, _MaxAlt), inside) :-
    DX is X - CX, DY is Y - CY,
    Dist2 is DX*DX + DY*DY,
    Dist2 =< R*R, !.
geofence(_ID, _Pos, _Zone, outside).

% ---------------------------------------------------------------
% resolve_conflict(+D1, +D2, +Priority1, -Resolution)
% Decide which drone should yield.
% Resolution: yield(D1) | yield(D2) | coordinate(D1,D2)
% ---------------------------------------------------------------
resolve_conflict(D1, _D2, P1, yield(D1)) :-
    P1 < 50, !.
resolve_conflict(_D1, D2, P1, yield(D2)) :-
    P1 >= 50, !.
resolve_conflict(D1, D2, _P1, coordinate(D1, D2)).

% ---------------------------------------------------------------
% safe_altitude(+Class, +DroneType, -MaxAlt)
% Returns recommended ceiling for drone type within airspace class.
% ---------------------------------------------------------------
safe_altitude(class_g, recreational, 120).
safe_altitude(class_g, cargo,        100).
safe_altitude(class_e, cargo,        500).
safe_altitude(class_e, survey,       550).
safe_altitude(class_d, cargo,        1100).
safe_altitude(class_c, cargo,        2800).
safe_altitude(_Class,  emergency,    9999).

% ---------------------------------------------------------------
% allowed_in_class(+DroneType, +Class)
% Defines which drone types may enter each airspace class.
% ---------------------------------------------------------------
allowed_in_class(emergency,    _Class).
allowed_in_class(cargo,        class_g).
allowed_in_class(cargo,        class_e).
allowed_in_class(cargo,        class_d).
allowed_in_class(survey,       class_g).
allowed_in_class(survey,       class_e).
allowed_in_class(recreational, class_g).
