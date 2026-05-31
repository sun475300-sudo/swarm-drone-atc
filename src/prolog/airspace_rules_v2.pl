% Airspace Rules v2 — SDACS Phase 660
:- module(airspace_rules_v2, [airspace_class/2, conflict/3, priority/2]).
airspace_class(drone, class_g).
conflict(A, B, zone) :- near(A, B).
priority(atc, drone).
geofence(restricted, 200).
