-- Phase 595: Safety Critical — 드론 안전 임계 시스템 (Ada)
-- SPARK/Ada safety-critical drone control implementation.
with Ada.Text_IO;       use Ada.Text_IO;
with Ada.Float_Text_IO;
with Ada.Real_Time;     use Ada.Real_Time;

-- Package specification for Safety_Critical module
package Safety_Critical is
   PHASE : constant Integer := 595;

   -- Safety status enumeration
   type Safety_Status is (Safe, Warning, Critical, Emergency);

   -- Drone state record
   type Drone_State is record
      ID       : Integer;
      Altitude : Float;   -- metres
      Battery  : Float;   -- percentage 0-100
      Velocity : Float;   -- m/s
      Status   : Safety_Status;
   end record;

   -- Safety envelope bounds
   MIN_ALTITUDE   : constant Float := 10.0;
   MAX_ALTITUDE   : constant Float := 400.0;
   MIN_BATTERY    : constant Float := 15.0;
   MAX_VELOCITY   : constant Float := 25.0;
   CRITICAL_BAT   : constant Float := 10.0;
   EMERGENCY_BAT  : constant Float := 5.0;

   -- Assess drone safety status
   procedure Assess_Safety (State : in out Drone_State);

   -- Determine corrective action
   function Required_Action (State : Drone_State) return String;

end Safety_Critical;

-- Package body
package body Safety_Critical is

   procedure Assess_Safety (State : in out Drone_State) is
   begin
      if State.Battery <= EMERGENCY_BAT or
         State.Altitude < 0.0 or
         State.Velocity > MAX_VELOCITY * 1.5
      then
         State.Status := Emergency;
      elsif State.Battery <= CRITICAL_BAT or
            State.Altitude < MIN_ALTITUDE
      then
         State.Status := Critical;
      elsif State.Battery <= MIN_BATTERY or
            State.Altitude > MAX_ALTITUDE or
            State.Velocity > MAX_VELOCITY
      then
         State.Status := Warning;
      else
         State.Status := Safe;
      end if;
   end Assess_Safety;

   function Required_Action (State : Drone_State) return String is
   begin
      case State.Status is
         when Emergency => return "IMMEDIATE_LANDING";
         when Critical  => return "RETURN_TO_HOME";
         when Warning   => return "REDUCE_SPEED_AND_ALTITUDE";
         when Safe      => return "CONTINUE_MISSION";
      end case;
   end Required_Action;

end Safety_Critical;

-- Main procedure
with Ada.Text_IO;    use Ada.Text_IO;
with Safety_Critical; use Safety_Critical;

procedure Safety_Critical_Main is

   States : array (1..5) of Drone_State := (
     (1, 50.0,  80.0, 10.0, Safe),
     (2, 5.0,   70.0,  8.0, Safe),   -- below min altitude
     (3, 100.0,  8.0,  5.0, Safe),   -- critical battery
     (4, 200.0, 50.0, 30.0, Safe),   -- over velocity
     (5, 350.0,  4.0, 15.0, Safe)    -- emergency battery
   );

begin
   Put_Line ("Phase " & Integer'Image (PHASE) & ": Safety_Critical — 드론 안전 임계 시스템");
   Put_Line ("Assessing " & Integer'Image (States'Length) & " drones...");

   for S of States loop
      Assess_Safety (S);
      Put_Line ("  Drone " & Integer'Image (S.ID)
               & " alt=" & Float'Image (S.Altitude)
               & " bat=" & Float'Image (S.Battery)
               & " status=" & Safety_Status'Image (S.Status)
               & " action=" & Required_Action (S));
   end loop;

   Put_Line ("Safety_Critical assessment complete — Phase " & Integer'Image (PHASE));
end Safety_Critical_Main;
