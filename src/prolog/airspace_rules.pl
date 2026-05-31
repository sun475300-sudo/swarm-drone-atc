% P573: AirspaceRules - Prolog declarative airspace rule engine
% Phase 573: Class-based airspace management with conflict and priority resolution

:- module(airspace_rules, [
    airspace_class/2,
    conflict/3,
    priority/2,
    geofence/3,
    can_fly/3,
    resolve_conflict/3
]).

% Airspace class definitions
% airspace_class(Zone, Class)
airspace_class(urban_center, class_c).
airspace_class(suburban, class_d).
airspace_class(rural, class_g).
airspace_class(airport_5km, class_c).
airspace_class(restricted, class_r).
airspace_class(national_park, class_g).
airspace_class(emergency_corridor, class_e).

% Priority rules: higher number = higher priority
priority(emergency, 100).
priority(medical_delivery, 90).
priority(law_enforcement, 85).
priority(infrastructure_inspection, 70).
priority(commercial_delivery, 60).
priority(survey_mapping, 50).
priority(recreational, 10).

% conflict(DroneA, DroneB, Reason)
conflict(A, B, separation_violation) :-
    drone_position(A, Xa, Ya, Za),
    drone_position(B, Xb, Yb, Zb),
    Dx is Xa - Xb, Dy is Ya - Yb, Dz is Za - Zb,
    Dist is sqrt(Dx*Dx + Dy*Dy + Dz*Dz),
    min_separation(MinSep),
    Dist < MinSep,
    A \= B.

conflict(A, _, altitude_violation) :-
    drone_position(A, _, _, Z),
    max_altitude(MaxAlt),
    (Z > MaxAlt ; Z < 30).

% geofence(Zone, Boundary, DronePosition)
geofence(urban_center, circle(0,0,1000), pos(X,Y,_)) :-
    Dist is sqrt(X*X + Y*Y),
    Dist < 1000.

geofence(restricted, poly([_|_]), _) :- fail.

% can_fly(DroneType, Zone, Altitude)
can_fly(emergency, _, _) :- !.
can_fly(_, class_r, _) :- !, fail.
can_fly(Type, Zone, Alt) :-
    airspace_class(Zone, Class),
    altitude_ok(Class, Alt),
    mission_allowed(Type, Class).

altitude_ok(class_c, Alt) :- Alt >= 30, Alt =< 120.
altitude_ok(class_d, Alt) :- Alt >= 30, Alt =< 150.
altitude_ok(class_g, Alt) :- Alt >= 30, Alt =< 400.
altitude_ok(class_e, Alt) :- Alt >= 30, Alt =< 150.

mission_allowed(recreational, class_g).
mission_allowed(commercial_delivery, class_g).
mission_allowed(commercial_delivery, class_d).
mission_allowed(survey_mapping, class_g).
mission_allowed(medical_delivery, _).
mission_allowed(infrastructure_inspection, _).

% resolve_conflict(DroneA, DroneB, Resolution)
resolve_conflict(A, B, hold(LowerPriority)) :-
    drone_mission(A, MissionA),
    drone_mission(B, MissionB),
    priority(MissionA, PA),
    priority(MissionB, PB),
    (PA >= PB -> LowerPriority = B ; LowerPriority = A).

% Facts (to be asserted at runtime)
:- dynamic drone_position/4.
:- dynamic drone_mission/2.
min_separation(5.0).
max_altitude(150.0).
