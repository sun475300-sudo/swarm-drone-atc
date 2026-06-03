-- Phase 585: Safety-Critical System — Ada
-- SDACS DO-178C compliant safety monitor for drone operations

with Ada.Real_Time;          use Ada.Real_Time;
with Ada.Text_IO;            use Ada.Text_IO;
with Ada.Numerics.Elementary_Functions; use Ada.Numerics.Elementary_Functions;

package body Safety_Critical is

   -- Internal state protected object
   protected body Safety_Monitor is

      procedure Update_State (New_State : Drone_State) is
      begin
         Current_State := New_State;
         Check_Safety_Conditions;
      end Update_State;

      function Get_State return Drone_State is
      begin
         return Current_State;
      end Get_State;

      function Is_Safe return Boolean is
      begin
         return Safety_Status = Safe;
      end Is_Safe;

      function Get_Safety_Status return Safety_Level is
      begin
         return Safety_Status;
      end Get_Safety_Status;

      procedure Trigger_Emergency_Stop is
      begin
         Safety_Status := Emergency;
         Emergency_Count := Emergency_Count + 1;
      end Trigger_Emergency_Stop;

      function Emergency_Count_Val return Natural is
      begin
         return Emergency_Count;
      end Emergency_Count_Val;

      procedure Check_Safety_Conditions is
      begin
         -- Check altitude envelope
         if Current_State.Altitude > Max_Altitude then
            Safety_Status := Critical;
         elsif Current_State.Altitude < Min_Altitude and
               Current_State.Mode /= Landing then
            Safety_Status := Warning;
         -- Check battery level
         elsif Current_State.Battery_Pct <= Critical_Battery then
            Safety_Status := Emergency;
            Emergency_Count := Emergency_Count + 1;
         elsif Current_State.Battery_Pct <= Low_Battery then
            Safety_Status := Critical;
         -- Check speed envelope
         elsif Current_State.Speed > Max_Speed then
            Safety_Status := Warning;
         else
            Safety_Status := Safe;
         end if;
      end Check_Safety_Conditions;

   end Safety_Monitor;

   -- TMR voter: majority vote across 3 redundant readings
   function TMR_Vote (A, B, C : Float) return Float is
      Tolerance : constant Float := 0.5;
   begin
      if abs (A - B) <= Tolerance then
         return (A + B) / 2.0;
      elsif abs (A - C) <= Tolerance then
         return (A + C) / 2.0;
      elsif abs (B - C) <= Tolerance then
         return (B + C) / 2.0;
      else
         -- No agreement — return median
         declare
            Min_Val : Float := Float'Min (A, Float'Min (B, C));
            Max_Val : Float := Float'Max (A, Float'Max (B, C));
         begin
            return A + B + C - Min_Val - Max_Val;
         end;
      end if;
   end TMR_Vote;

   -- Watchdog task body
   task body Watchdog is
      Period    : constant Time_Span := Milliseconds (100);
      Next_Time : Time := Clock;
      Heartbeat : Natural := 0;
   begin
      loop
         -- Feed watchdog
         Heartbeat := Heartbeat + 1;

         -- Check safety monitor
         if not Monitor.Is_Safe then
            Put_Line ("[WATCHDOG] Safety violation detected! " &
                      Safety_Level'Image (Monitor.Get_Safety_Status));
         end if;

         -- Periodic tick
         Next_Time := Next_Time + Period;
         delay until Next_Time;
      end loop;
   end Watchdog;

   -- Geofence check
   function Within_Geofence
     (Lat, Lon   : Float;
      Center_Lat : Float := 37.5665;
      Center_Lon : Float := 126.9780;
      Radius_M   : Float := 1000.0) return Boolean
   is
      Earth_R   : constant Float := 6_371_000.0;
      Pi        : constant Float := 3.14159265;
      Deg2Rad   : constant Float := Pi / 180.0;
      DLat      : Float := (Lat - Center_Lat) * Deg2Rad;
      DLon      : Float := (Lon - Center_Lon) * Deg2Rad;
      A         : Float;
      Distance  : Float;
   begin
      A := Sin (DLat / 2.0) ** 2 +
           Cos (Lat * Deg2Rad) * Cos (Center_Lat * Deg2Rad) *
           Sin (DLon / 2.0) ** 2;
      Distance := Earth_R * 2.0 * Arctan (Sqrt (A), Sqrt (1.0 - A));
      return Distance <= Radius_M;
   end Within_Geofence;

end Safety_Critical;
