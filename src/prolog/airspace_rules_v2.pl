% Phase 657 — Airspace Rules v2 (Prolog)
% 드론 공역 규정 논리 추론 엔진

:- module(airspace_rules, [
    is_authorized/3,
    separation_ok/4,
    altitude_legal/2,
    conflict_resolution/4
]).

% ── 공역 등급 정의 ────────────────────────────────────────────
airspace_class(controlled,   max_alt(120), requires_clearance(true)).
airspace_class(uncontrolled, max_alt(400), requires_clearance(false)).
airspace_class(restricted,   max_alt(0),   requires_clearance(true)).
airspace_class(emergency,    max_alt(500), requires_clearance(true)).

% ── 드론 운용 허가 검사 ───────────────────────────────────────
is_authorized(DroneID, Class, _Altitude) :-
    airspace_class(Class, _, requires_clearance(false)),
    registered_drone(DroneID).

is_authorized(DroneID, Class, Altitude) :-
    airspace_class(Class, max_alt(MaxAlt), requires_clearance(true)),
    Altitude =< MaxAlt,
    registered_drone(DroneID),
    has_clearance(DroneID, Class).

% ── 수평/수직 분리 기준 ───────────────────────────────────────
% 수평 분리 30m, 수직 분리 15m
separation_ok(X1, Y1, X2, Y2) :-
    Dist2D is sqrt((X1 - X2)^2 + (Y1 - Y2)^2),
    Dist2D >= 30.0.

separation_ok_3d(X1, Y1, Z1, X2, Y2, Z2) :-
    separation_ok(X1, Y1, X2, Y2), !.
separation_ok_3d(_, _, Z1, _, _, Z2) :-
    VertDist is abs(Z1 - Z2),
    VertDist >= 15.0.

% ── 고도 합법성 검사 ─────────────────────────────────────────
altitude_legal(Altitude, Class) :-
    airspace_class(Class, max_alt(MaxAlt), _),
    MaxAlt > 0,
    Altitude >= 20,
    Altitude =< MaxAlt.

% ── 충돌 해결 조언 ───────────────────────────────────────────
% 우선순위: 긴급 > 착륙 > 순항 > 이륙
conflict_resolution(emergency,     _, right_of_way, advisory(yield)).
conflict_resolution(cruise, landing, right_of_way, advisory(yield)).
conflict_resolution(_,      _,       equal_priority, advisory(altitude_adjust)).

% ── 팩트 DB (예시) ────────────────────────────────────────────
registered_drone('D-001').
registered_drone('D-002').
has_clearance('D-001', controlled).
has_clearance('D-002', controlled).
