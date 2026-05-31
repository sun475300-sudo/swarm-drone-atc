-- Phase 655 — TMR Voter v2 (Ada)
-- Triple Modular Redundancy 투표기 — 드론 센서 내결함성

with Ada.Text_IO; use Ada.Text_IO;
with Ada.Float_Text_IO;

package body TMR_Voter is

   --------------------
   -- Majority_Vote  --
   --------------------

   function Majority_Vote (A, B, C : Float) return Vote_Result is
      Tolerance : constant Float := 0.01;
      AB_Close  : constant Boolean := abs (A - B) <= Tolerance;
      AC_Close  : constant Boolean := abs (A - C) <= Tolerance;
      BC_Close  : constant Boolean := abs (B - C) <= Tolerance;
   begin
      if AB_Close and AC_Close then
         -- 세 채널 모두 일치
         return (Value => (A + B + C) / 3.0, Confidence => 1.0, Faulty => None);
      elsif AB_Close then
         -- C가 이상값
         return (Value => (A + B) / 2.0, Confidence => 0.67, Faulty => Channel_C);
      elsif AC_Close then
         -- B가 이상값
         return (Value => (A + C) / 2.0, Confidence => 0.67, Faulty => Channel_B);
      elsif BC_Close then
         -- A가 이상값
         return (Value => (B + C) / 2.0, Confidence => 0.67, Faulty => Channel_A);
      else
         -- 세 채널 모두 불일치 — 중앙값 사용
         declare
            Sorted_1, Sorted_2, Sorted_3 : Float;
         begin
            if A <= B and then A <= C then
               Sorted_1 := A;
               if B <= C then Sorted_2 := B; Sorted_3 := C;
               else            Sorted_2 := C; Sorted_3 := B; end if;
            elsif B <= A and then B <= C then
               Sorted_1 := B;
               if A <= C then Sorted_2 := A; Sorted_3 := C;
               else            Sorted_2 := C; Sorted_3 := A; end if;
            else
               Sorted_1 := C;
               if A <= B then Sorted_2 := A; Sorted_3 := B;
               else            Sorted_2 := B; Sorted_3 := A; end if;
            end if;
            pragma Unreferenced (Sorted_1, Sorted_3);
            return (Value => Sorted_2, Confidence => 0.33, Faulty => All_Diverged);
         end;
      end if;
   end Majority_Vote;

end TMR_Voter;
