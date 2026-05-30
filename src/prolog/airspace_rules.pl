% Phase 573: airspace_rules — Prolog 기반 공역 규칙 엔진
% SDACS Airspace Rules for Drone Traffic Management

:- module(airspace_rules, [
    airspace_class/2,
    conflict/3,
    priority/2,
    geofence/3,
    check_drone/2,
    resolve_conflict/3
]).

%% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
%% 공역 등급 분류 (airspace_class)
%% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

% airspace_class(+고도m, -등급)
airspace_class(Alt, class_a) :- Alt >= 300, !.
airspace_class(Alt, class_b) :- Alt >= 150, Alt < 300, !.
airspace_class(Alt, class_c) :- Alt >= 120, Alt < 150, !.
airspace_class(Alt, class_d) :- Alt >= 50,  Alt < 120, !.
airspace_class(Alt, class_g) :- Alt < 50, !.

% 등급별 허용 조건
class_allowed(class_a, _DroneType) :- fail.  % 상업 공역: 드론 불허
class_allowed(class_b, commercial).
class_allowed(class_c, commercial).
class_allowed(class_c, research).
class_allowed(class_d, commercial).
class_allowed(class_d, research).
class_allowed(class_d, recreational).
class_allowed(class_g, _).                   % 개방 공역: 모든 드론

%% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
%% 충돌 감지 (conflict)
%% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

% conflict(+DroneA, +DroneB, -충돌유형)
% 각 드론: drone(ID, Lat, Lon, Alt, Speed, Type)
conflict(
    drone(IdA, LatA, LonA, AltA, _, _),
    drone(IdB, LatB, LonB, AltB, _, _),
    horizontal_conflict
) :-
    IdA \= IdB,
    HorizDist is sqrt((LatA-LatB)^2 + (LonA-LonB)^2) * 111320,
    HorizDist < 30.0,   % 30m 수평 분리 최소값
    abs(AltA - AltB) < 10.0.

conflict(
    drone(IdA, _, _, AltA, _, _),
    drone(IdB, _, _, AltB, _, _),
    altitude_conflict
) :-
    IdA \= IdB,
    abs(AltA - AltB) < 5.0.

conflict(
    drone(IdA, LatA, LonA, AltA, _, _),
    drone(IdB, LatB, LonB, AltB, _, _),
    near_miss
) :-
    IdA \= IdB,
    Dist is sqrt((LatA-LatB)^2 * 111320^2 + (LonA-LonB)^2 * 111320^2 + (AltA-AltB)^2),
    Dist < 10.0.

%% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
%% 우선순위 규칙 (priority)
%% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

% priority(+드론타입, -우선순위값) — 높을수록 우선
priority(emergency,    100).
priority(medical,       90).
priority(commercial,    70).
priority(cargo,         60).
priority(research,      50).
priority(recreational,  30).
priority(unknown,        0).

% 두 드론 중 우선순위가 높은 드론 선택
higher_priority(TypeA, TypeB, TypeA) :-
    priority(TypeA, PA), priority(TypeB, PB), PA >= PB, !.
higher_priority(_, TypeB, TypeB).

%% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
%% 지오펜스 (geofence)
%% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

% 금지 구역 데이터베이스
geofence_zone(airport_A, 37.4690, 126.4510, 3.0, 0, 300).  % 인천공항
geofence_zone(airport_B, 37.5580, 126.7930, 2.5, 0, 300).  % 김포공항
geofence_zone(nfz_01,    37.5665, 126.9780, 1.0, 0, 200).  % 청와대

% geofence(+위도, +경도, -규칙)
geofence(Lat, Lon, no_fly) :-
    geofence_zone(_, ZLat, ZLon, Radius, _, _),
    Dist is sqrt((Lat-ZLat)^2 + (Lon-ZLon)^2) * 111320 / 1000,  % km
    Dist < Radius.

geofence(_, _, allowed) :- \+ geofence(_, _, no_fly).

%% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
%% 드론 종합 검사
%% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

check_drone(drone(Id, Lat, Lon, Alt, _, Type), Result) :-
    airspace_class(Alt, Class),
    ( class_allowed(Class, Type)
    -> ( geofence(Lat, Lon, GeoResult),
         ( GeoResult = no_fly
         -> Result = violation(Id, geofence_violation)
         ;  Result = ok(Id, Class) ))
    ;  Result = violation(Id, class_not_allowed(Class, Type)) ).

%% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
%% 충돌 해결
%% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

resolve_conflict(
    drone(IdA, _, _, _, _, TypeA) = DroneA,
    drone(IdB, _, _, _, _, TypeB) = DroneB,
    Resolution
) :-
    higher_priority(TypeA, TypeB, WinnerType),
    ( WinnerType = TypeA
    -> Resolution = yield(IdB, to_drone(IdA))
    ;  Resolution = yield(IdA, to_drone(IdB)) ).
