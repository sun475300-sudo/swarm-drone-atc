%% Phase 573: Airspace Rules Engine — Prolog
%% 공역 규칙 추론 시스템: 비행 허가, 충돌 판정, 우선순위 결정.

%% ─── 공역 분류 ───
airspace_class(alpha, 0, 18000).       % Class A: 계기비행 전용
airspace_class(bravo, 0, 10000).       % Class B: 대형 공항
airspace_class(charlie, 0, 4000).      % Class C: 중형 공항
airspace_class(delta, 0, 2500).        % Class D: 소형 공항
airspace_class(echo, 0, 1200).         % Class E: 비관제
airspace_class(golf, 0, 400).          % Class G: 비관제 저고도

%% ─── 드론 유형 ───
drone_type(multirotor, small, 25).     % 최대 25kg
drone_type(multirotor, medium, 150).
drone_type(fixed_wing, small, 25).
drone_type(fixed_wing, large, 600).
drone_type(vtol, medium, 150).

%% ─── 비행 제한 ───
max_altitude(drone, 400).              % 드론 최대 고도 (ft AGL)
min_separation_h(50).                  % 수평 최소 분리 (m)
min_separation_v(15).                  % 수직 최소 분리 (m)

%% ─── 비행 허가 규칙 ───
flight_permitted(DroneId, Class, Alt) :-
    airspace_class(Class, MinAlt, MaxAlt),
    Alt >= MinAlt,
    Alt =< MaxAlt,
    max_altitude(drone, MaxDroneAlt),
    Alt =< MaxDroneAlt,
    has_clearance(DroneId, Class).

%% 자동 허가 (Class G, E)
has_clearance(_, golf).
has_clearance(_, echo).

%% 관제 허가 필요 (Class B, C, D)
has_clearance(DroneId, bravo) :- atc_approved(DroneId, bravo).
has_clearance(DroneId, charlie) :- atc_approved(DroneId, charlie).
has_clearance(DroneId, delta) :- atc_approved(DroneId, delta).

%% ─── 충돌 판정 ───
conflict(Drone1, Drone2) :-
    position(Drone1, X1, Y1, Z1),
    position(Drone2, X2, Y2, Z2),
    Drone1 \= Drone2,
    DX is X2 - X1, DY is Y2 - Y1,
    DistH is sqrt(DX*DX + DY*DY),
    DistV is abs(Z2 - Z1),
    min_separation_h(MinH),
    min_separation_v(MinV),
    DistH < MinH,
    DistV < MinV.

%% ─── 우선순위 규칙 ───
priority(emergency, 1).
priority(medical, 2).
priority(law_enforcement, 3).
priority(commercial, 4).
priority(recreational, 5).

higher_priority(Drone1, Drone2) :-
    mission_type(Drone1, Type1),
    mission_type(Drone2, Type2),
    priority(Type1, P1),
    priority(Type2, P2),
    P1 < P2.

%% ─── 회피 조언 ───
resolution_advisory(Drone1, Drone2, Advisory) :-
    conflict(Drone1, Drone2),
    (higher_priority(Drone1, Drone2) ->
        Advisory = yield(Drone2)
    ;
        Advisory = yield(Drone1)
    ).

%% 수직 회피
vertical_resolution(Drone, climb) :-
    position(Drone, _, _, Z),
    max_altitude(drone, MaxAlt),
    Z + 30 =< MaxAlt.

vertical_resolution(Drone, descend) :-
    position(Drone, _, _, Z),
    Z - 30 >= 0.

%% ─── 지오펜스 ───
geofence(no_fly_zone_1, circle, 1000, 2000, 500).   % cx, cy, radius
geofence(restricted_area, circle, 3000, 3000, 1000).

inside_geofence(Drone, Zone) :-
    position(Drone, X, Y, _),
    geofence(Zone, circle, CX, CY, R),
    DX is X - CX, DY is Y - CY,
    Dist is sqrt(DX*DX + DY*DY),
    Dist < R.

violation(Drone, geofence_breach, Zone) :-
    inside_geofence(Drone, Zone).

%% ─── 테스트 데이터 ───
position(drone_001, 100, 200, 50).
position(drone_002, 130, 210, 55).
position(drone_003, 5000, 5000, 100).
mission_type(drone_001, commercial).
mission_type(drone_002, emergency).
mission_type(drone_003, recreational).
atc_approved(drone_001, charlie).

%% ─── 쿼리 예시 ───
%% ?- conflict(drone_001, drone_002).
%% ?- resolution_advisory(drone_001, drone_002, A).
%% ?- flight_permitted(drone_001, golf, 200).
%% ?- inside_geofence(drone_001, no_fly_zone_1).
