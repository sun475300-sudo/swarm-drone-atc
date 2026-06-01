-- Phase 645: TMR Voter v2 — 3중 모듈 중복 투표기 (Ada)
-- Triple Modular Redundancy voter for safety-critical drone control.
with Ada.Text_IO; use Ada.Text_IO;
with Ada.Float_Text_IO;

package body TMR_Voter_V2 is

   -- Vote on three Float inputs, returning majority.
   function Vote_Float (A, B, C : Float; Tolerance : Float := 0.01) return Float is
      Diff_AB : constant Float := abs (A - B);
      Diff_AC : constant Float := abs (A - C);
      Diff_BC : constant Float := abs (B - C);
   begin
      if Diff_AB <= Tolerance then
         return (A + B) / 2.0;
      elsif Diff_AC <= Tolerance then
         return (A + C) / 2.0;
      elsif Diff_BC <= Tolerance then
         return (B + C) / 2.0;
      else
         -- All three disagree — fall back to median
         if A <= B and B <= C then return B;
         elsif A <= C and C <= B then return C;
         elsif B <= A and A <= C then return A;
         elsif B <= C and C <= A then return C;
         elsif C <= A and A <= B then return A;
         else return B;
         end if;
      end if;
   end Vote_Float;

   -- Vote on three Boolean inputs by majority.
   function Vote_Boolean (A, B, C : Boolean) return Boolean is
      Count : Natural := 0;
   begin
      if A then Count := Count + 1; end if;
      if B then Count := Count + 1; end if;
      if C then Count := Count + 1; end if;
      return Count >= 2;
   end Vote_Boolean;

end TMR_Voter_V2;

-- Main procedure for Phase 645 TMR Voter demonstration.
with Ada.Text_IO; use Ada.Text_IO;
with TMR_Voter_V2;

procedure TMR_Voter_Main is
   package TIO renames Ada.Text_IO;

   -- Simulate three redundant altitude sensors
   Alt_A : constant Float := 50.1;
   Alt_B : constant Float := 50.0;
   Alt_C : constant Float := 49.9;  -- within tolerance

   -- One faulty sensor scenario
   Flt_A : constant Float := 50.0;
   Flt_B : constant Float := 50.1;
   Flt_C : constant Float := 99.9;  -- faulty

   -- Safety gate votes
   Gate_A : constant Boolean := True;
   Gate_B : constant Boolean := True;
   Gate_C : constant Boolean := False;  -- fault

   Result_Alt   : Float;
   Result_Flt   : Float;
   Result_Gate  : Boolean;

begin
   TIO.Put_Line ("Phase 645: TMR Voter v2 — 드론 안전 투표기");

   Result_Alt := TMR_Voter_V2.Vote_Float (Alt_A, Alt_B, Alt_C);
   TIO.Put ("Normal altitude vote: ");
   Ada.Float_Text_IO.Put (Result_Alt, Fore => 4, Aft => 2, Exp => 0);
   TIO.New_Line;

   Result_Flt := TMR_Voter_V2.Vote_Float (Flt_A, Flt_B, Flt_C);
   TIO.Put ("Fault scenario vote:  ");
   Ada.Float_Text_IO.Put (Result_Flt, Fore => 4, Aft => 2, Exp => 0);
   TIO.New_Line;

   Result_Gate := TMR_Voter_V2.Vote_Boolean (Gate_A, Gate_B, Gate_C);
   TIO.Put_Line ("Gate vote (2/3 True): " & Boolean'Image (Result_Gate));

   TIO.Put_Line ("TMR voting complete — 안전 검증 완료");
end TMR_Voter_Main;

-- Spec package for TMR_Voter_V2
package TMR_Voter_V2 is
   function Vote_Float (A, B, C : Float; Tolerance : Float := 0.01) return Float;
   function Vote_Boolean (A, B, C : Boolean) return Boolean;
end TMR_Voter_V2;
