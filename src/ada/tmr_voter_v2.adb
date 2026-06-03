-- Phase 645: TMR Voter v2 — Ada
-- SDACS Enhanced Triple Modular Redundancy voter for safety-critical sensors

with Ada.Text_IO; use Ada.Text_IO;
with Ada.Numerics.Elementary_Functions; use Ada.Numerics.Elementary_Functions;

package body TMR_Voter_V2 is

   function Vote_Float (A, B, C : Float; Tolerance : Float := 0.5) return Vote_Result is
      Diff_AB : constant Float := abs (A - B);
      Diff_AC : constant Float := abs (A - C);
      Diff_BC : constant Float := abs (B - C);
   begin
      -- Majority vote: at least 2 of 3 must agree within tolerance
      if Diff_AB <= Tolerance then
         return (Value => (A + B) / 2.0, Agreement => Two_Of_Three, Faulty => C_Sensor);
      elsif Diff_AC <= Tolerance then
         return (Value => (A + C) / 2.0, Agreement => Two_Of_Three, Faulty => B_Sensor);
      elsif Diff_BC <= Tolerance then
         return (Value => (B + C) / 2.0, Agreement => Two_Of_Three, Faulty => A_Sensor);
      else
         -- No agreement: use median
         declare
            Min_Val : Float := Float'Min (A, Float'Min (B, C));
            Max_Val : Float := Float'Max (A, Float'Max (B, C));
            Median  : Float := A + B + C - Min_Val - Max_Val;
         begin
            return (Value => Median, Agreement => None, Faulty => All_Sensors);
         end;
      end if;
   end Vote_Float;

   function Vote_Integer (A, B, C : Integer) return Integer is
   begin
      if A = B then return A;
      elsif A = C then return A;
      elsif B = C then return B;
      else return (A + B + C) / 3;
      end if;
   end Vote_Integer;

   procedure Run_Self_Test is
      R : Vote_Result;
   begin
      R := Vote_Float (10.0, 10.1, 10.05);
      Put_Line ("Phase 645 TMR Voter v2 — Test 1 (agreement): " &
                Float'Image (R.Value));
      R := Vote_Float (10.0, 20.0, 10.1);
      Put_Line ("Test 2 (faulty B): " & Float'Image (R.Value));
   end Run_Self_Test;

end TMR_Voter_V2;
