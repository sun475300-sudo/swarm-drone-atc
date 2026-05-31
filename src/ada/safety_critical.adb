-- Phase 595 — Ada Safety_Critical package implementation
-- SDACS safety-critical flight envelope monitoring for swarm drones

with Ada.Text_IO;         use Ada.Text_IO;
with Ada.Float_Text_IO;   use Ada.Float_Text_IO;
with Ada.Integer_Text_IO; use Ada.Integer_Text_IO;

package body Safety_Critical is

   -- Internal constants
   Max_Drones : constant := 64;

   -- --------------------
   -- Drone state record
   -- --------------------
   type Drone_State is record
      Id           : Natural;
      Active       : Boolean;
      Altitude_M   : Float;
      Speed_Mps    : Float;
      Battery_Pct  : Float;
      Fault_Count  : Natural;
      Safe         : Boolean;
   end record;

   Drone_Table : array (1 .. Max_Drones) of Drone_State;

   -- --------------------
   -- Initialize the Safety_Critical subsystem
   -- --------------------
   procedure Initialize is
   begin
      for I in Drone_Table'Range loop
         Drone_Table (I) := (Id           => I,
                              Active       => False,
                              Altitude_M   => 0.0,
                              Speed_Mps    => 0.0,
                              Battery_Pct  => 100.0,
                              Fault_Count  => 0,
                              Safe         => True);
      end loop;
      Put_Line ("Safety_Critical: initialized " & Natural'Image (Max_Drones) & " drone slots");
   end Initialize;

   -- --------------------
   -- Register a drone unit
   -- --------------------
   procedure Register_Drone (Id : in Natural) is
   begin
      if Id in 1 .. Max_Drones then
         Drone_Table (Id).Active := True;
         Put_Line ("Safety_Critical: registered drone " & Natural'Image (Id));
      end if;
   end Register_Drone;

   -- --------------------
   -- Update telemetry for a drone
   -- --------------------
   procedure Update_Telemetry (Id         : in Natural;
                                Altitude   : in Float;
                                Speed      : in Float;
                                Battery    : in Float) is
   begin
      if Id not in 1 .. Max_Drones or else not Drone_Table (Id).Active then
         return;
      end if;
      Drone_Table (Id).Altitude_M  := Altitude;
      Drone_Table (Id).Speed_Mps   := Speed;
      Drone_Table (Id).Battery_Pct := Battery;
   end Update_Telemetry;

   -- --------------------
   -- Core safety envelope check — Safety_Critical constraint validation
   -- --------------------
   function Check_Safe (Id : in Natural) return Boolean is
      D          : Drone_State;
      Is_Safe    : Boolean := True;
   begin
      if Id not in 1 .. Max_Drones or else not Drone_Table (Id).Active then
         return False;
      end if;
      D := Drone_Table (Id);

      -- Altitude Safety_Critical bounds: 0 – 400 m
      if D.Altitude_M < 0.0 or D.Altitude_M > 400.0 then
         Put_Line ("Safety_Critical ALERT: drone " & Natural'Image (Id) &
                   " altitude out of bounds: " & Float'Image (D.Altitude_M));
         Is_Safe := False;
      end if;

      -- Speed Safety_Critical limit: <= 30 m/s
      if D.Speed_Mps > 30.0 then
         Put_Line ("Safety_Critical ALERT: drone " & Natural'Image (Id) &
                   " overspeed: " & Float'Image (D.Speed_Mps));
         Is_Safe := False;
      end if;

      -- Battery Safety_Critical low threshold: >= 10 %
      if D.Battery_Pct < 10.0 then
         Put_Line ("Safety_Critical WARN: drone " & Natural'Image (Id) &
                   " low battery: " & Float'Image (D.Battery_Pct) & "%");
         Is_Safe := False;
      end if;

      Drone_Table (Id).Safe := Is_Safe;
      if Is_Safe then
         Drone_Table (Id).Fault_Count := 0;
      else
         Drone_Table (Id).Fault_Count := Drone_Table (Id).Fault_Count + 1;
      end if;

      return Is_Safe;
   end Check_Safe;

   -- --------------------
   -- Sweep all active drones for safety violations
   -- --------------------
   procedure Run_Safety_Sweep is
      Violations : Natural := 0;
   begin
      Put_Line ("Safety_Critical: running sweep...");
      for I in Drone_Table'Range loop
         if Drone_Table (I).Active then
            if not Check_Safe (I) then
               Violations := Violations + 1;
            end if;
         end if;
      end loop;
      Put_Line ("Safety_Critical: sweep complete — violations: " & Natural'Image (Violations));
   end Run_Safety_Sweep;

   -- --------------------
   -- Print status for one drone
   -- --------------------
   procedure Print_Drone_Status (Id : in Natural) is
      D : Drone_State;
   begin
      if Id not in 1 .. Max_Drones then return; end if;
      D := Drone_Table (Id);
      Put_Line ("Drone " & Natural'Image (Id) &
                " alt=" & Float'Image (D.Altitude_M) &
                " spd=" & Float'Image (D.Speed_Mps) &
                " bat=" & Float'Image (D.Battery_Pct) &
                " safe=" & Boolean'Image (D.Safe) &
                " faults=" & Natural'Image (D.Fault_Count));
   end Print_Drone_Status;

end Safety_Critical;
