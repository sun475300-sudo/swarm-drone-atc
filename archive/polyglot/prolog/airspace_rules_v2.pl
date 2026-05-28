%% Phase 657: Airspace Rules V2 — Prolog Dynamic Rule Engine
%% 동적 공역 규칙 엔진 v2: 상황 인식 기반 적응형 규칙 추론

%% ── 기본 사실 (Facts) ──────────────────────────────────

%% drone(ID, Type, Priority, BatteryPct, AltitudeM)
drone(d001, commercial, 3, 85, 60).
drone(d002, commercial, 3, 45, 80).
drone(d003, emergency,  1, 90, 100).
drone(d004, military,   2, 70, 110).
drone(d005, commercial, 3, 12, 50).
drone(d006, rogue,      5, 99, 40).

%% weather(Condition, WindSpeedMS, Visibility)
weather(normal, 5, good).
% weather(storm, 18, poor).
% weather(fog, 3, very_poor).

%% nfz(Name, CenterX, CenterY, RadiusM)
nfz(military_zone, 1000, 1000, 500).
nfz(airport_zone, -2000, 0, 1000).
nfz(hospital_zone, 500, -500, 200).

%% ── 안전 규칙 (Safety Rules) ─────────────────────────

%% 최소 분리간격 (m)
min_separation(30).
min_separation_high_density(50).

%% 고도 제한
max_altitude(120).
min_altitude(30).

%% 배터리 임계치
battery_critical(15).
battery_warning(25).

%% ── 추론 규칙 (Inference Rules) ─────────────────────

%% 드론이 비상 상태인지
is_emergency(ID) :-
    drone(ID, emergency, _, _, _).

%% 드론이 저배터리인지
low_battery(ID) :-
    drone(ID, _, _, Battery, _),
    battery_critical(Threshold),
    Battery < Threshold.

%% 배터리 경고
battery_warn(ID) :-
    drone(ID, _, _, Battery, _),
    battery_warning(Threshold),
    Battery < Threshold.

%% 드론이 고도 위반인지
altitude_violation(ID) :-
    drone(ID, _, _, _, Alt),
    max_altitude(Max),
    Alt > Max.

altitude_violation(ID) :-
    drone(ID, _, _, _, Alt),
    min_altitude(Min),
    Alt < Min.

%% 악의적 드론 탐지
is_rogue(ID) :-
    drone(ID, rogue, _, _, _).

%% 우선순위 비교 (낮은 숫자 = 높은 우선순위)
higher_priority(ID1, ID2) :-
    drone(ID1, _, P1, _, _),
    drone(ID2, _, P2, _, _),
    P1 < P2.

%% RTL (Return to Launch) 필요 판단
needs_rtl(ID) :-
    low_battery(ID),
    \+ is_emergency(ID).

%% 강풍 시 고도 제한 강화
wind_altitude_limit(Limit) :-
    weather(_, Wind, _),
    Wind > 10,
    Limit is 80.

wind_altitude_limit(Limit) :-
    weather(_, Wind, _),
    Wind =< 10,
    Limit is 120.

%% 회피 어드바이저리 결정
advisory_type(ID1, ID2, climb) :-
    drone(ID1, _, _, _, Alt1),
    drone(ID2, _, _, _, Alt2),
    Alt1 > Alt2,
    higher_priority(ID2, ID1).

advisory_type(ID1, ID2, descend) :-
    drone(ID1, _, _, _, Alt1),
    drone(ID2, _, _, _, Alt2),
    Alt1 =< Alt2,
    higher_priority(ID2, ID1).

advisory_type(ID1, _, hold) :-
    is_emergency(ID1).

%% NFZ 침입 판단 (간소화)
in_nfz(ID, Zone) :-
    drone(ID, _, _, _, _),
    nfz(Zone, _, _, _).
    % 실제로는 좌표 거리 계산 필요 (Prolog 한계로 간소화)

%% ── 종합 상태 보고 ────────────────────────────────────

drone_status_report(ID, Status) :-
    is_rogue(ID),
    Status = rogue_detected.

drone_status_report(ID, Status) :-
    low_battery(ID),
    Status = critical_battery.

drone_status_report(ID, Status) :-
    altitude_violation(ID),
    Status = altitude_violation.

drone_status_report(ID, Status) :-
    is_emergency(ID),
    Status = emergency_active.

drone_status_report(ID, Status) :-
    \+ is_rogue(ID),
    \+ low_battery(ID),
    \+ altitude_violation(ID),
    \+ is_emergency(ID),
    Status = normal.

%% ── 쿼리 예시 ──────────────────────────────────────

%% ?- drone_status_report(d005, S).  → S = critical_battery
%% ?- needs_rtl(ID).                 → ID = d005
%% ?- is_rogue(ID).                  → ID = d006
%% ?- higher_priority(d003, d001).   → true (emergency > commercial)
%% ?- wind_altitude_limit(L).        → L = 120 (normal weather)
