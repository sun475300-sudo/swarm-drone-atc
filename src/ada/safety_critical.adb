-- Safety_Critical — Ada for SDACS safety-critical control loop
-- Phase 595

with Ada.Real_Time;       use Ada.Real_Time;
with Ada.Text_IO;         use Ada.Text_IO;
with Ada.Numerics.Float_Random;

package body Safety_Critical is

   type Drone_State_Record is record
      Altitude    : Float := 0.0;
      Speed       : Float := 0.0;
      Battery_Pct : Float := 100.0;
      Is_Armed    : Boolean := False;
      Fault_Code  : Natural := 0;
   end record;

   Current_State : Drone_State_Record;

   -- ── Safety Invariants ──────────────────────────────────────

   function Is_Safe (State : Drone_State_Record) return Boolean is
   begin
      return State.Altitude >= 0.0 and then
             State.Altitude <= 10000.0 and then
             State.Speed >= 0.0 and then
             State.Speed <= 50.0 and then
             State.Battery_Pct >= 0.0 and then
             State.Battery_Pct <= 100.0 and then
             State.Fault_Code = 0;
   end Is_Safe;

   -- ── Emergency Procedures ───────────────────────────────────

   procedure Emergency_Land is
   begin
      Put_Line ("EMERGENCY LAND triggered");
      Current_State.Is_Armed   := False;
      Current_State.Fault_Code := 1;
   end Emergency_Land;

   procedure Return_To_Launch is
   begin
      Put_Line ("RTL triggered");
      Current_State.Is_Armed   := False;
      Current_State.Fault_Code := 2;
   end Return_To_Launch;

   -- ── Watchdog Task ──────────────────────────────────────────

   task type Watchdog_Task (Period_Ms : Natural) is
      pragma Priority (10);
   end Watchdog_Task;

   task body Watchdog_Task is
      Next_Time : Time := Clock;
      Period    : constant Time_Span := Milliseconds (Period_Ms);
   begin
      loop
         delay until Next_Time;
         if not Is_Safe (Current_State) then
            Put_Line ("WATCHDOG: unsafe state detected — triggering emergency land");
            Emergency_Land;
         end if;
         if Current_State.Battery_Pct < 15.0 and then Current_State.Is_Armed then
            Put_Line ("WATCHDOG: low battery — triggering RTL");
            Return_To_Launch;
         end if;
         Next_Time := Next_Time + Period;
      end loop;
   end Watchdog_Task;

   Watchdog : Watchdog_Task (100);   -- 100ms period

   -- ── Control Loop ───────────────────────────────────────────

   procedure Run_Control_Cycle (Altitude_Cmd : Float; Speed_Cmd : Float) is
   begin
      if not Current_State.Is_Armed then
         return;
      end if;

      -- Saturate commands to safe limits
      Current_State.Altitude := Float'Min (Float'Max (Altitude_Cmd, 0.0), 10000.0);
      Current_State.Speed    := Float'Min (Float'Max (Speed_Cmd, 0.0), 50.0);

      -- Simulate battery drain
      Current_State.Battery_Pct :=
         Current_State.Battery_Pct - (Current_State.Speed * 0.01);
      Current_State.Battery_Pct :=
         Float'Max (0.0, Current_State.Battery_Pct);
   end Run_Control_Cycle;

   procedure Arm is
   begin
      if Is_Safe (Current_State) then
         Current_State.Is_Armed := True;
         Put_Line ("Drone armed.");
      else
         Put_Line ("Cannot arm: unsafe state.");
      end if;
   end Arm;

end Safety_Critical;
