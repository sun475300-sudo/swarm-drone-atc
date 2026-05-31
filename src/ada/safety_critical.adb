-- P595: Safety_Critical - Ada safety-critical drone control
-- Phase 595: SPARK-annotated safety-critical drone avionics

with Ada.Text_IO; use Ada.Text_IO;
with Ada.Float_Text_IO;

package body Safety_Critical is

   -- Safety boundary constants
   MIN_ALTITUDE    : constant Float := 30.0;
   MAX_ALTITUDE    : constant Float := 150.0;
   MIN_SEPARATION  : constant Float := 5.0;
   MIN_BATTERY     : constant Float := 0.15;
   MAX_SPEED       : constant Float := 20.0;
   CRITICAL_BATTERY: constant Float := 0.05;

   -- Check if position is within safe altitude bounds
   function Is_Safe_Altitude (Z : Float) return Boolean is
   begin
      return Z >= MIN_ALTITUDE and then Z <= MAX_ALTITUDE;
   end Is_Safe_Altitude;

   -- Check if battery level is above minimum
   function Is_Battery_Safe (Level : Float) return Boolean is
   begin
      return Level >= MIN_BATTERY;
   end Is_Battery_Safe;

   -- Check if battery is critical
   function Is_Battery_Critical (Level : Float) return Boolean is
   begin
      return Level < CRITICAL_BATTERY;
   end Is_Battery_Critical;

   -- Compute 3D distance between two positions
   function Distance_3D (A, B : Position_3D) return Float is
      Dx, Dy, Dz : Float;
   begin
      Dx := B.X - A.X;
      Dy := B.Y - A.Y;
      Dz := B.Z - A.Z;
      return Float (Sqrt (Float (Dx * Dx + Dy * Dy + Dz * Dz)));
   end Distance_3D;

   -- Check minimum separation between two drones
   function Check_Separation (A, B : Drone_State) return Safety_Check_Result is
      Dist : Float;
   begin
      Dist := Distance_3D (A.Position, B.Position);
      if Dist < MIN_SEPARATION then
         return (Passed => False,
                 Violation => Separation_Violation,
                 Value => Dist);
      end if;
      return (Passed => True, Violation => No_Violation, Value => Dist);
   end Check_Separation;

   -- Perform full safety check on a drone
   function Check_Drone_Safety (D : Drone_State) return Safety_Report is
      Report : Safety_Report := (Drone_Id => D.Id,
                                  All_Clear => True,
                                  Violations => 0);
   begin
      -- Altitude check
      if not Is_Safe_Altitude (D.Position.Z) then
         Report.All_Clear := False;
         Report.Violations := Report.Violations + 1;
      end if;

      -- Battery check
      if not Is_Battery_Safe (D.Battery_Pct) then
         Report.All_Clear := False;
         Report.Violations := Report.Violations + 1;
      end if;

      -- Speed check
      declare
         Speed : Float;
      begin
         Speed := Float (Sqrt (Float (
            D.Velocity.X * D.Velocity.X +
            D.Velocity.Y * D.Velocity.Y +
            D.Velocity.Z * D.Velocity.Z)));
         if Speed > MAX_SPEED then
            Report.All_Clear := False;
            Report.Violations := Report.Violations + 1;
         end if;
      end;

      return Report;
   end Check_Drone_Safety;

   -- TMR voter: return majority of three values
   function TMR_Vote (A, B, C : Float) return Float is
      Tol : constant Float := 0.01;
   begin
      if abs (A - B) <= Tol then return (A + B) / 2.0;
      elsif abs (A - C) <= Tol then return (A + C) / 2.0;
      elsif abs (B - C) <= Tol then return (B + C) / 2.0;
      else
         -- All differ: return median
         if (A <= B and then B <= C) or else (C <= B and then B <= A) then
            return B;
         elsif (B <= A and then A <= C) or else (C <= A and then A <= B) then
            return A;
         else return C;
         end if;
      end if;
   end TMR_Vote;

end Safety_Critical;
