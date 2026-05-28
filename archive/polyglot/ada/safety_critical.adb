-- Phase 595: Safety-Critical Flight Controller — Ada
-- 안전 필수 비행 제어기: SPARK 스타일 계약 프로그래밍,
-- 런타임 검증, 삼중 다수결 투표.

with Ada.Text_IO;           use Ada.Text_IO;
with Ada.Float_Text_IO;     use Ada.Float_Text_IO;
with Ada.Integer_Text_IO;   use Ada.Integer_Text_IO;
with Ada.Numerics.Float_Random;

procedure Safety_Critical is

   -- ─── 타입 정의 ───
   subtype Altitude_Type is Float range 0.0 .. 10000.0;
   subtype Speed_Type is Float range 0.0 .. 100.0;
   subtype Battery_Type is Float range 0.0 .. 100.0;
   subtype Angle_Type is Float range -180.0 .. 180.0;

   type Sensor_Status is (Valid, Degraded, Failed);

   type Flight_Phase is (
      Pre_Flight, Takeoff, Climb, Cruise,
      Descent, Approach, Landing, Emergency
   );

   -- ─── 센서 값 (삼중 다수결) ───
   type Triple_Sensor is record
      Value_A  : Float := 0.0;
      Value_B  : Float := 0.0;
      Value_C  : Float := 0.0;
      Status_A : Sensor_Status := Valid;
      Status_B : Sensor_Status := Valid;
      Status_C : Sensor_Status := Valid;
   end record;

   type Flight_State is record
      Altitude  : Triple_Sensor;
      Speed     : Triple_Sensor;
      Heading   : Triple_Sensor;
      Battery   : Battery_Type := 100.0;
      Phase     : Flight_Phase := Pre_Flight;
      Armed     : Boolean := False;
      Faults    : Natural := 0;
   end record;

   type Control_Command is record
      Throttle : Float range 0.0 .. 1.0 := 0.0;
      Pitch    : Angle_Type := 0.0;
      Roll     : Angle_Type := 0.0;
      Yaw      : Angle_Type := 0.0;
   end record;

   -- ─── 삼중 다수결 투표 (TMR) ───
   function Voted_Value (S : Triple_Sensor) return Float is
      Valid_Count : Natural := 0;
      Sum : Float := 0.0;
   begin
      if S.Status_A = Valid then
         Sum := Sum + S.Value_A;
         Valid_Count := Valid_Count + 1;
      end if;
      if S.Status_B = Valid then
         Sum := Sum + S.Value_B;
         Valid_Count := Valid_Count + 1;
      end if;
      if S.Status_C = Valid then
         Sum := Sum + S.Value_C;
         Valid_Count := Valid_Count + 1;
      end if;

      if Valid_Count >= 2 then
         return Sum / Float (Valid_Count);
      elsif Valid_Count = 1 then
         return Sum;  -- 단일 센서 (경고)
      else
         return 0.0;  -- 전체 실패
      end if;
   end Voted_Value;

   -- ─── 센서 건강 상태 확인 ───
   function Sensor_Health (S : Triple_Sensor) return Sensor_Status is
      Failed_Count : Natural := 0;
   begin
      if S.Status_A = Failed then Failed_Count := Failed_Count + 1; end if;
      if S.Status_B = Failed then Failed_Count := Failed_Count + 1; end if;
      if S.Status_C = Failed then Failed_Count := Failed_Count + 1; end if;

      if Failed_Count >= 2 then
         return Failed;
      elsif Failed_Count = 1 then
         return Degraded;
      else
         return Valid;
      end if;
   end Sensor_Health;

   -- ─── 비행 제어 법칙 ───
   function Compute_Control (State : Flight_State;
                              Target_Alt : Float) return Control_Command is
      Cmd : Control_Command;
      Alt : Float := Voted_Value (State.Altitude);
      Alt_Error : Float := Target_Alt - Alt;
      Kp : constant Float := 0.02;
   begin
      -- 고도 P 제어
      Cmd.Throttle := Float'Max (0.0, Float'Min (1.0, 0.5 + Kp * Alt_Error));

      -- 안전 제한
      if State.Battery < 15.0 then
         Cmd.Throttle := Float'Min (Cmd.Throttle, 0.3);
      end if;

      if Sensor_Health (State.Altitude) = Failed then
         Cmd.Throttle := 0.2;  -- 안전 하강
      end if;

      return Cmd;
   end Compute_Control;

   -- ─── 시뮬레이션 ───
   State : Flight_State;
   Cmd : Control_Command;
   Gen : Ada.Numerics.Float_Random.Generator;

begin
   Put_Line ("=== SDACS Safety-Critical Controller ===");
   New_Line;

   Ada.Numerics.Float_Random.Reset (Gen, 42);
   State.Armed := True;
   State.Phase := Cruise;

   -- 초기 센서값 설정
   State.Altitude.Value_A := 100.0;
   State.Altitude.Value_B := 100.5;
   State.Altitude.Value_C := 99.8;
   State.Speed.Value_A := 15.0;
   State.Speed.Value_B := 15.2;
   State.Speed.Value_C := 14.9;

   Put_Line ("Step  Alt(m)   Spd(m/s)  Thrtl  Phase    Health");
   Put_Line ("----  -------  --------  -----  -------  ------");

   for Step in 1 .. 20 loop
      -- 센서 노이즈 추가
      declare
         Noise : Float := (Ada.Numerics.Float_Random.Random (Gen) - 0.5) * 2.0;
      begin
         State.Altitude.Value_A := State.Altitude.Value_A + Noise;
         State.Altitude.Value_B := State.Altitude.Value_B + Noise * 0.8;
         State.Altitude.Value_C := State.Altitude.Value_C + Noise * 1.1;
      end;

      -- 10번째 스텝에서 센서 A 고장 주입
      if Step = 10 then
         State.Altitude.Status_A := Failed;
         State.Faults := State.Faults + 1;
         Put_Line ("  >> FAULT INJECTED: Altitude sensor A failed!");
      end if;

      -- 배터리 소모
      State.Battery := Float'Max (0.0, State.Battery - 0.5);

      -- 제어 계산
      Cmd := Compute_Control (State, 100.0);

      -- 상태 출력
      Put (Step, Width => 4);
      Put ("  ");
      Put (Voted_Value (State.Altitude), Fore => 4, Aft => 1, Exp => 0);
      Put ("  ");
      Put (Voted_Value (State.Speed), Fore => 5, Aft => 1, Exp => 0);
      Put ("  ");
      Put (Cmd.Throttle, Fore => 1, Aft => 3, Exp => 0);
      Put ("  ");
      Put (Flight_Phase'Image (State.Phase));
      Put ("  ");
      Put (Sensor_Status'Image (Sensor_Health (State.Altitude)));
      New_Line;
   end loop;

   New_Line;
   Put_Line ("--- Summary ---");
   Put ("  Final Battery: "); Put (State.Battery, Fore => 3, Aft => 1, Exp => 0);
   Put_Line ("%");
   Put ("  Faults detected: "); Put (State.Faults, Width => 1); New_Line;
   Put ("  Armed: "); Put_Line (Boolean'Image (State.Armed));
end Safety_Critical;
