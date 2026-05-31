% Airspace Rules — SDACS Phase 573
:- module(airspace_rules, [airspace_class/2, conflict/3, priority/2]).
airspace_class(drone, class_g).
conflict(A, B, zone) :- near(A, B).
priority(atc, drone).
geofence(restricted, 100).
