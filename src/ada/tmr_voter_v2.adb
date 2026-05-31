-- Phase 655 — Triple Modular Redundancy Voter v2 in Ada
with Ada.Text_IO; use Ada.Text_IO;

package body TMR_Voter_V2 is

   function Vote (A, B, C : Float) return Float is
      Threshold : constant Float := 0.1;
   begin
      if abs (A - B) <= Threshold then return (A + B) / 2.0;
      elsif abs (A - C) <= Threshold then return (A + C) / 2.0;
      elsif abs (B - C) <= Threshold then return (B + C) / 2.0;
      else
         Put_Line ("TMR: No majority — using median");
         return (if A + B + C - Float'Min(A, Float'Min(B, C)) - Float'Max(A, Float'Max(B, C)) = A then A
                 elsif A + B + C - Float'Min(A, Float'Min(B, C)) - Float'Max(A, Float'Max(B, C)) = B then B
                 else C);
      end if;
   end Vote;

end TMR_Voter_V2;

package TMR_Voter_V2 is
   function Vote (A, B, C : Float) return Float;
end TMR_Voter_V2;
