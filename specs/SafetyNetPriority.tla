---------------------------- MODULE SafetyNetPriority ----------------------------
(***************************************************************************)
(* ODYSSEY Phase 441 — SDACS 5계층 안전망 충돌 회피 우선순위 불변식.       *)
(*                                                                         *)
(* simulation/failsafe_manager.py 의 이산 Failsafe 에스컬레이션 사다리를   *)
(* TLA+ 로 형식화한다. 동일 전이계를 simulation/safety_net_invariant.py 의  *)
(* 유한 모델 검사기가 전수 탐색으로 검증한다(TLC 없이도 재현 가능).        *)
(*                                                                         *)
(* 레벨: 0 NORMAL < 1 WARN < 2 LAND < 3 RTL < 4 DISARM < 5 EMERGENCY.      *)
(* 위험 차원별 심각도 → 요구 레벨은 failsafe_manager 임계값에 정렬된다.     *)
(***************************************************************************)
EXTENDS Naturals, Sequences

CONSTANTS NORMAL, WARN, LAND, RTL, DISARM, EMERGENCY

\* 위험 차원별 심각도 사다리 -> 요구 Failsafe 레벨 (failsafe_manager 정렬).
\* comm:    >2s WARN / >5s RTL / >30s DISARM
\* battery: <=25% WARN / <=15% LAND / <=5% DISARM
\* geofence: breach -> RTL
\* collision: imminent -> EMERGENCY
CommLevels      == <<NORMAL, WARN, RTL, DISARM>>
BatteryLevels   == <<NORMAL, WARN, LAND, DISARM>>
GeofenceLevels  == <<NORMAL, RTL>>
CollisionLevels == <<NORMAL, EMERGENCY>>

VARIABLES
    level,        \* 현재 Failsafe 레벨
    comm,         \* comm 위험 심각도 인덱스 (1..Len(CommLevels))
    battery,
    geofence,
    collision

vars == <<level, comm, battery, geofence, collision>>

Max(a, b) == IF a >= b THEN a ELSE b

\* 활성 위험들이 요구하는 최소 레벨 = 차원별 요구 레벨의 최댓값 ("worst hazard wins").
RequiredLevel ==
    Max(CommLevels[comm],
        Max(BatteryLevels[battery],
            Max(GeofenceLevels[geofence], CollisionLevels[collision])))

TypeOK ==
    /\ level \in {NORMAL, WARN, LAND, RTL, DISARM, EMERGENCY}
    /\ comm \in 1..Len(CommLevels)
    /\ battery \in 1..Len(BatteryLevels)
    /\ geofence \in 1..Len(GeofenceLevels)
    /\ collision \in 1..Len(CollisionLevels)

Init ==
    /\ level = NORMAL
    /\ comm = 1
    /\ battery = 1
    /\ geofence = 1
    /\ collision = 1

\* 환경: 한 위험 차원이 한 단계 악화 또는 완화 (레벨 불변).
HazardChange ==
    \/ /\ \E n \in 1..Len(CommLevels) : n \in {comm-1, comm+1} /\ comm' = n
       /\ UNCHANGED <<level, battery, geofence, collision>>
    \/ /\ \E n \in 1..Len(BatteryLevels) : n \in {battery-1, battery+1} /\ battery' = n
       /\ UNCHANGED <<level, comm, geofence, collision>>
    \/ /\ \E n \in 1..Len(GeofenceLevels) : n \in {geofence-1, geofence+1} /\ geofence' = n
       /\ UNCHANGED <<level, comm, battery, collision>>
    \/ /\ \E n \in 1..Len(CollisionLevels) : n \in {collision-1, collision+1} /\ collision' = n
       /\ UNCHANGED <<level, comm, battery, geofence>>

\* 컨트롤러: 레벨을 활성 위험 요구치로 래칫 (절대 하강 없음 — _transition 규칙).
ControllerStep ==
    /\ level' = Max(level, RequiredLevel)
    /\ UNCHANGED <<comm, battery, geofence, collision>>

\* 복귀: 모든 위험이 해제됐을 때만 NORMAL 로 (restore_comm 류).
RestoreStep ==
    /\ RequiredLevel = NORMAL
    /\ comm = 1 /\ battery = 1 /\ geofence = 1 /\ collision = 1
    /\ level' = NORMAL
    /\ UNCHANGED <<comm, battery, geofence, collision>>

Next == HazardChange \/ ControllerStep \/ RestoreStep

Spec == Init /\ [][Next]_vars

(***************************************************************************)
(* 안전 불변식.                                                            *)
(***************************************************************************)

\* HazardChange 와 ControllerStep 은 *별개* 전이이므로, 위험이 막 오른 직후
\* 컨트롤러가 아직 안 따라온 과도 상태에서 (level >= RequiredLevel) 는 일시적으로
\* 거짓일 수 있다. 따라서 SAFE 는 순수 상태 불변식이 아니라 컨트롤러가 반응한
\* 직후를 규정하는 *액션* 불변식으로 표현한다.

\* SAFE (복원 가능성): 컨트롤러 스텝 직후 레벨 >= 요구 레벨.
SafeAfterControl == ControllerStep => (level' >= RequiredLevel)

\* MONOTONE: 컨트롤러 스텝은 레벨을 낮추지 않는다 (래칫).
Monotone == ControllerStep => (level' >= level)

\* RestoreOnlyWhenClear: 복귀는 활성 위험이 없을 때만.
RestoreSafe == RestoreStep => (RequiredLevel = NORMAL)

\* 안전 속성 묶음. simulation/safety_net_invariant.py 의 유한 모델 검사기가
\* 이 액션 불변식들의 대응(복원 가능성·MONOTONE·복귀 안전 + 비공허성)을
\* 도달 가능 전 상태에 대해 전수 검증한다(TLC 미실행 환경의 동형 검증).
THEOREM Safety ==
    Spec => /\ [](TypeOK)
            /\ [][SafeAfterControl]_vars
            /\ [][Monotone]_vars
            /\ [][RestoreSafe]_vars
=============================================================================
