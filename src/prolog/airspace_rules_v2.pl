% airspace_rules_v2.pl - Enhanced airspace rules v2 for SDACS
:- module(airspace_rules_v2, [
    airspace_class/2, conflict/3, priority/2, geofence/3,
    utm_class/2, deconflict/3, altitude_band/3
]).

airspace_class(class_a, above_18000_ft).
airspace_class(class_b, controlled).
airspace_class(class_g, uncontrolled).

utm_class(open, below_120m).
utm_class(specific, requires_authorization).
utm_class(certified, high_risk).

priority(emergency, 1).
priority(medical, 2).
priority(commercial, 4).
priority(recreational, 5).

conflict(A, B, separation_violation) :-
    drone_position(A, PA), drone_position(B, PB),
    separation(PA, PB, D), D < 30.

geofence(airport, circular, [radius(5000)]).
geofence(restricted, polygon, [military]).
geofence(no_fly, circular, [radius(2000)]).

altitude_band(low, 0, 120).
altitude_band(medium, 120, 400).
altitude_band(high, 400, 18000).

deconflict(A, B, yield(B, A)) :-
    priority(TA, PA), priority(TB, PB),
    drone_type(A, TA), drone_type(B, TB),
    PA < PB.

separation(point(X1,Y1,Z1), point(X2,Y2,Z2), D) :-
    D is sqrt((X2-X1)^2+(Y2-Y1)^2+(Z2-Z1)^2).
