-- P655: TMR Voter v2 - Ada stub
-- Triple Modular Redundancy voter for safety-critical drone control

with Ada.Text_IO; use Ada.Text_IO;

package body TMR_Voter_V2 is

   function Vote (A, B, C : Float) return Float is
      Threshold : constant Float := 0.01;
   begin
      -- Majority voting: return value agreed upon by at least 2 of 3
      if abs (A - B) <= Threshold then
         return (A + B) / 2.0;
      elsif abs (A - C) <= Threshold then
         return (A + C) / 2.0;
      elsif abs (B - C) <= Threshold then
         return (B + C) / 2.0;
      else
         -- All three disagree: return median
         if (A <= B and B <= C) or (C <= B and B <= A) then
            return B;
         elsif (B <= A and A <= C) or (C <= A and A <= B) then
            return A;
         else
            return C;
         end if;
      end if;
   end Vote;

   function Vote_Integer (A, B, C : Integer) return Integer is
   begin
      if A = B then return A;
      elsif A = C then return A;
      elsif B = C then return B;
      else return B;
      end if;
   end Vote_Integer;

   function Is_Valid (A, B, C : Float; Max_Deviation : Float) return Boolean is
      Max_Val : Float := Float'Max (Float'Max (A, B), C);
      Min_Val : Float := Float'Min (Float'Min (A, B), C);
   begin
      return (Max_Val - Min_Val) <= Max_Deviation;
   end Is_Valid;

end TMR_Voter_V2;
