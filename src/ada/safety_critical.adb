-- Phase 595: safety_critical — Ada 기반 안전 임계 시스템
-- SDACS Safety_Critical Module for Drone Flight Safety

with Ada.Text_IO;
with Ada.Float_Text_IO;
with Ada.Numerics.Elementary_Functions;

package body Safety_Critical is

   use Ada.Text_IO;
   use Ada.Numerics.Elementary_Functions;

   -- 드론 상태 유효성 검사
   function Validate_Drone_State(State : Drone_State) return Validation_Result is
      Errors : Error_Array := (others => Error_None);
      Count  : Natural := 0;
   begin
      -- 배터리 범위 검사
      if State.Battery < 0.0 or State.Battery > 100.0 then
         Count := Count + 1;
         Errors(Count) := Error_Battery_Out_Of_Range;
      end if;

      -- 고도 범위 검사 (0 ~ 120m)
      if State.Altitude < -5.0 or State.Altitude > 120.0 then
         Count := Count + 1;
         Errors(Count) := Error_Altitude_Exceeded;
      end if;

      -- GPS 유효성 검사
      if abs(State.Latitude)  > 90.0 or
         abs(State.Longitude) > 180.0 then
         Count := Count + 1;
         Errors(Count) := Error_GPS_Invalid;
      end if;

      return Validation_Result'(
         Is_Valid    => Count = 0,
         Error_Count => Count,
         Errors      => Errors
      );
   end Validate_Drone_State;

   -- 충돌 위험 거리 계산 (Haversine)
   function Compute_Separation(A, B : Drone_State) return Float is
      R    : constant Float := 6_371_000.0;
      DLat : Float := (B.Latitude  - A.Latitude)  * (Float'(3.14159265) / 180.0);
      DLon : Float := (B.Longitude - A.Longitude) * (Float'(3.14159265) / 180.0);
      SinA : Float := Sin(DLat / 2.0);
      SinO : Float := Sin(DLon / 2.0);
      CosA : Float := Cos(A.Latitude * (Float'(3.14159265) / 180.0));
      CosB : Float := Cos(B.Latitude * (Float'(3.14159265) / 180.0));
      A_Val: Float := SinA * SinA + CosA * CosB * SinO * SinO;
   begin
      return R * 2.0 * Arctan(Sqrt(A_Val) / Sqrt(1.0 - A_Val));
   end Compute_Separation;

   -- 안전 규칙 엔진
   function Check_Safety_Rules(State : Drone_State) return Safety_Decision is
   begin
      -- 배터리 15% 미만: 즉시 귀환
      if State.Battery < 15.0 then
         return Safety_Decision'(
            Action  => Action_RTL,
            Reason  => "배터리 임계값 미만",
            Urgency => Urgency_Immediate
         );
      end if;

      -- 배터리 20% 미만: 경고 + 귀환 권고
      if State.Battery < 20.0 then
         return Safety_Decision'(
            Action  => Action_RTL,
            Reason  => "배터리 낮음",
            Urgency => Urgency_High
         );
      end if;

      -- 고도 초과: 하강 명령
      if State.Altitude > 115.0 then
         return Safety_Decision'(
            Action  => Action_Descend,
            Reason  => "최대 고도 접근",
            Urgency => Urgency_High
         );
      end if;

      -- 정상 비행
      return Safety_Decision'(
         Action  => Action_Continue,
         Reason  => "정상 비행",
         Urgency => Urgency_None
      );
   end Check_Safety_Rules;

   -- 감시 타이머 처리
   procedure Update_Watchdog(WD : in out Watchdog_Timer; Current_Time : Float) is
   begin
      if Current_Time - WD.Last_Heartbeat > WD.Timeout_Seconds then
         WD.Triggered := True;
      else
         WD.Triggered := False;
      end if;
   end Update_Watchdog;

end Safety_Critical;

-- 사양 파일
package Safety_Critical is

   -- 오류 코드
   type Error_Code is (
      Error_None,
      Error_Battery_Out_Of_Range,
      Error_Altitude_Exceeded,
      Error_GPS_Invalid,
      Error_Communication_Lost,
      Error_Sensor_Failure
   );

   type Error_Array is array(1..5) of Error_Code;

   -- 드론 상태
   type Drone_State is record
      Drone_Id    : Natural;
      Latitude    : Float;
      Longitude   : Float;
      Altitude    : Float;
      Battery     : Float;  -- 0.0 ~ 100.0
      Speed       : Float;
      Armed       : Boolean;
      Mode        : String(1..12);
   end record;

   -- 유효성 검사 결과
   type Validation_Result is record
      Is_Valid    : Boolean;
      Error_Count : Natural;
      Errors      : Error_Array;
   end record;

   -- 안전 행동
   type Safety_Action is (
      Action_Continue,
      Action_RTL,
      Action_Land,
      Action_Descend,
      Action_Hover,
      Action_Emergency_Stop
   );

   -- 긴급도
   type Urgency_Level is (
      Urgency_None,
      Urgency_Low,
      Urgency_High,
      Urgency_Immediate
   );

   -- 안전 결정
   type Safety_Decision is record
      Action  : Safety_Action;
      Reason  : String(1..50);
      Urgency : Urgency_Level;
   end record;

   -- 감시 타이머
   type Watchdog_Timer is record
      Last_Heartbeat   : Float;
      Timeout_Seconds  : Float;
      Triggered        : Boolean;
   end record;

   function  Validate_Drone_State(State : Drone_State) return Validation_Result;
   function  Compute_Separation(A, B : Drone_State) return Float;
   function  Check_Safety_Rules(State : Drone_State) return Safety_Decision;
   procedure Update_Watchdog(WD : in out Watchdog_Timer; Current_Time : Float);

end Safety_Critical;

-- 메인 테스트 프로그램
with Ada.Text_IO;
with Safety_Critical; use Safety_Critical;

procedure Main_Safety_Critical is
   use Ada.Text_IO;
   S1 : Drone_State := (
      Drone_Id  => 0,
      Latitude  => 37.500,
      Longitude => 127.000,
      Altitude  => 50.0,
      Battery   => 95.0,
      Speed     => 5.0,
      Armed     => True,
      Mode      => "GUIDED      "
   );
   S2 : Drone_State := (
      Drone_Id  => 1,
      Latitude  => 37.501,
      Longitude => 127.001,
      Altitude  => 52.0,
      Battery   => 14.0,
      Speed     => 4.0,
      Armed     => True,
      Mode      => "GUIDED      "
   );
   R1, R2 : Validation_Result;
   D1, D2 : Safety_Decision;
begin
   Put_Line("SDACS Safety_Critical System — Phase 595");
   New_Line;

   R1 := Validate_Drone_State(S1);
   R2 := Validate_Drone_State(S2);

   Put_Line("드론 0 유효성: " & Boolean'Image(R1.Is_Valid));
   Put_Line("드론 1 유효성: " & Boolean'Image(R2.Is_Valid));

   D1 := Check_Safety_Rules(S1);
   D2 := Check_Safety_Rules(S2);

   Put_Line("드론 0 결정: " & Safety_Action'Image(D1.Action));
   Put_Line("드론 1 결정: " & Safety_Action'Image(D2.Action) & " (" & D2.Reason & ")");

   New_Line;
   Put_Line("안전 임계 시스템 처리 완료.");
end Main_Safety_Critical;
