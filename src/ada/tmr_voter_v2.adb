-- tmr_voter_v2.adb - Triple Modular Redundancy voter v2 for SDACS
with Ada.Text_IO; use Ada.Text_IO;

package body TMR_Voter_V2 is

   function Vote (A, B, C : Float; Tolerance : Float := 0.01) return Vote_Result is
      Diff_AB : Float := abs (A - B);
      Diff_BC : Float := abs (B - C);
      Diff_AC : Float := abs (A - C);
   begin
      if Diff_AB <= Tolerance then
         return (Valid => True, Value => (A + B) / 2.0, Faulty => None);
      elsif Diff_BC <= Tolerance then
         return (Valid => True, Value => (B + C) / 2.0, Faulty => Module_A);
      elsif Diff_AC <= Tolerance then
         return (Valid => True, Value => (A + C) / 2.0, Faulty => Module_B);
      else
         return (Valid => False, Value => (A + B + C) / 3.0, Faulty => Unknown);
      end if;
   end Vote;

   function Validate_Safety (Result : Vote_Result) return Boolean is
   begin
      return Result.Valid and Result.Faulty = None;
   end Validate_Safety;

end TMR_Voter_V2;
