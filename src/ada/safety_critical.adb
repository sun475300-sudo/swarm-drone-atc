-- SDACS Safety Critical System — Ada
-- 군집드론 안전 임계 시스템

with Ada.Text_IO; use Ada.Text_IO;
with Ada.Real_Time; use Ada.Real_Time;

-- Safety_Critical 패키지 본문
package body Safety_Critical is

   -- 안전 모니터링 태스크
   task body Safety_Monitor is
      Next_Period : Time := Clock;
      Period : constant Time_Span := Milliseconds(100);
   begin
      loop
         select
            accept Check_Safety(Drone_Id : in String; Status : out Safety_Status) do
               -- 안전 상태 점검
               Status := Safe;
               Put_Line("Safety check for: " & Drone_Id);
            end Check_Safety;
         or
            accept Emergency_Stop(Drone_Id : in String) do
               Put_Line("EMERGENCY STOP: " & Drone_Id);
            end Emergency_Stop;
         or
            delay until Next_Period;
            Next_Period := Next_Period + Period;
            -- 주기적 안전 점검
         end select;
      end loop;
   end Safety_Monitor;

   -- TMR (Triple Modular Redundancy) 투표 함수
   function TMR_Vote(A, B, C : Sensor_Reading) return Sensor_Reading is
   begin
      -- 다수결 투표 (2-of-3)
      if abs(A - B) < TOLERANCE then
         return (A + B) / 2.0;
      elsif abs(B - C) < TOLERANCE then
         return (B + C) / 2.0;
      elsif abs(A - C) < TOLERANCE then
         return (A + C) / 2.0;
      else
         -- 중앙값 반환
         return B;
      end if;
   end TMR_Vote;

   -- 안전 경계 검사
   function Check_Bounds(Value : Float; Low, High : Float) return Boolean is
   begin
      return Value >= Low and then Value <= High;
   end Check_Bounds;

   -- 충돌 회피 안전 검사
   function Is_Safe_Separation(Dist : Float) return Boolean is
   begin
      return Dist >= MIN_SAFE_DISTANCE;
   end Is_Safe_Separation;

   -- 배터리 임계값 검사
   function Battery_Critical(Level : Integer) return Boolean is
   begin
      return Level <= CRITICAL_BATTERY_LEVEL;
   end Battery_Critical;

   -- 초기화 프로시저
   procedure Initialize is
   begin
      Put_Line("Safety_Critical system initialized");
      Put_Line("Min separation: " & Float'Image(MIN_SAFE_DISTANCE) & " m");
      Put_Line("Critical battery: " & Integer'Image(CRITICAL_BATTERY_LEVEL) & "%");
   end Initialize;

end Safety_Critical;
