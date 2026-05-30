% SDACS Airspace Rules V2 — Prolog
% 군집드론 공역 규칙 v2

:- module(airspace_rules_v2, [
    airspace_class/2,
    conflict_resolution/3,
    priority_order/3,
    geofence_check/3,
    safe_separation/2
]).

% 공역 분류 (고도 기준, 미터)
airspace_class(Alt, class_g_low) :- Alt < 50.
airspace_class(Alt, class_g)     :- Alt >= 50, Alt < 120.
airspace_class(Alt, class_e)     :- Alt >= 120, Alt < 300.
airspace_class(Alt, class_d)     :- Alt >= 300, Alt < 600.
airspace_class(Alt, class_c)     :- Alt >= 600.

% 충돌 해결 규칙
conflict_resolution(DroneA, DroneB, climb) :-
    priority(DroneA, PA), priority(DroneB, PB), PA < PB.
conflict_resolution(DroneA, DroneB, descend) :-
    priority(DroneA, PA), priority(DroneB, PB), PA > PB.
conflict_resolution(_, _, lateral) :- true.

% 우선순위 순서 결정
priority_order(DroneA, DroneB, DroneA) :-
    priority(DroneA, PA), priority(DroneB, PB), PA =< PB.
priority_order(DroneA, DroneB, DroneB) :-
    priority(DroneA, PA), priority(DroneB, PB), PA > PB.

% 지오펜스 검사
geofence_check(X, Y, inside) :-
    geofence_center(CX, CY), geofence_radius(R),
    Dist is sqrt((X-CX)*(X-CX) + (Y-CY)*(Y-CY)),
    Dist =< R.
geofence_check(X, Y, outside) :-
    geofence_center(CX, CY), geofence_radius(R),
    Dist is sqrt((X-CX)*(X-CX) + (Y-CY)*(Y-CY)),
    Dist > R.

% 안전 간격 검사
safe_separation(Dist, safe)   :- Dist >= 10.0.
safe_separation(Dist, warning):- Dist >= 5.0, Dist < 10.0.
safe_separation(Dist, danger) :- Dist < 5.0.

% 팩트 정의
geofence_center(0.0, 0.0).
geofence_radius(1000.0).
priority(drone_001, 1).
priority(drone_002, 2).
priority(drone_003, 3).
