-- safety_critical.adb - Safety-Critical systems for SDACS
-- Ada implementation of triple modular redundancy for drone safety

with Ada.Text_IO;         use Ada.Text_IO;
with Ada.Float_Text_IO;   use Ada.Float_Text_IO;
with Ada.Numerics.Elementary_Functions; use Ada.Numerics.Elementary_Functions;

package body Safety_Critical is

   -- Vote on three redundant sensor readings using majority logic
   function TMR_Vote (A, B, C : Float) return Float is
      Tolerance : constant Float := 0.01;
      Diff_AB   : Float := abs (A - B);
      Diff_BC   : Float := abs (B - C);
      Diff_AC   : Float := abs (A - C);
   begin
      if Diff_AB <= Tolerance then
         return (A + B) / 2.0;  -- A and B agree
      elsif Diff_BC <= Tolerance then
         return (B + C) / 2.0;  -- B and C agree
      elsif Diff_AC <= Tolerance then
         return (A + C) / 2.0;  -- A and C agree
      else
         return (A + B + C) / 3.0;  -- All differ, use average
      end if;
   end TMR_Vote;

   -- Validate drone position is within safe bounds
   function Validate_Position (Pos : Position_3D) return Safety_Status is
      Max_Altitude  : constant Float := 400.0;  -- meters above ground
      Max_Coord     : constant Float := 50000.0;
   begin
      if Pos.Z < 0.0 then
         return (Safe => False, Code => ALTITUDE_VIOLATION,
                 Message => "Below ground level");
      elsif Pos.Z > Max_Altitude then
         return (Safe => False, Code => ALTITUDE_VIOLATION,
                 Message => "Altitude exceeds maximum");
      elsif abs (Pos.X) > Max_Coord or abs (Pos.Y) > Max_Coord then
         return (Safe => False, Code => BOUNDARY_VIOLATION,
                 Message => "Position outside airspace boundary");
      else
         return (Safe => True, Code => OK, Message => "Position valid");
      end if;
   end Validate_Position;

   -- Check battery level safety threshold
   function Check_Battery (Level : Natural) return Safety_Status is
   begin
      if Level < 5 then
         return (Safe => False, Code => BATTERY_CRITICAL,
                 Message => "Battery critically low - immediate landing required");
      elsif Level < 15 then
         return (Safe => False, Code => BATTERY_LOW,
                 Message => "Battery low - return to home");
      elsif Level < 25 then
         return (Safe => True, Code => BATTERY_WARNING,
                 Message => "Battery warning - consider landing soon");
      else
         return (Safe => True, Code => OK, Message => "Battery level nominal");
      end if;
   end Check_Battery;

   -- Perform full safety check on drone telemetry
   function Full_Safety_Check (State : Drone_State) return Safety_Report is
      Report : Safety_Report;
      Pos_Status  : Safety_Status := Validate_Position (State.Position);
      Batt_Status : Safety_Status := Check_Battery (State.Battery);
   begin
      Report.Drone_ID := State.Drone_ID;
      Report.Timestamp := State.Timestamp;
      Report.Position_OK := Pos_Status.Safe;
      Report.Battery_OK  := Batt_Status.Safe;
      Report.Overall_Safe := Pos_Status.Safe and Batt_Status.Safe;

      if not Report.Overall_Safe then
         if not Pos_Status.Safe then
            Report.Primary_Fault := Pos_Status.Code;
         else
            Report.Primary_Fault := Batt_Status.Code;
         end if;
      else
         Report.Primary_Fault := OK;
      end if;

      return Report;
   end Full_Safety_Check;

   -- Compute distance between two 3D positions
   function Distance_3D (A, B : Position_3D) return Float is
      DX : Float := B.X - A.X;
      DY : Float := B.Y - A.Y;
      DZ : Float := B.Z - A.Z;
   begin
      return Sqrt (DX*DX + DY*DY + DZ*DZ);
   end Distance_3D;

   -- Check separation between two drones
   function Check_Separation (A, B : Drone_State) return Boolean is
      Min_Sep : constant Float := 30.0;  -- 30 meter minimum separation
   begin
      return Distance_3D (A.Position, B.Position) >= Min_Sep;
   end Check_Separation;

end Safety_Critical;
