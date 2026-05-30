-- SDACS TMR Voter V2 — Ada
-- 군집드론 3중 모듈 중복 투표기 v2

with Ada.Text_IO; use Ada.Text_IO;

package body TMR_Voter_V2 is

   function Vote(A, B, C : Float) return Float is
      Tolerance : constant Float := 0.01;
   begin
      if abs(A - B) <= Tolerance then return (A + B) / 2.0;
      elsif abs(B - C) <= Tolerance then return (B + C) / 2.0;
      elsif abs(A - C) <= Tolerance then return (A + C) / 2.0;
      else return B;  -- 중앙값 대체
      end if;
   end Vote;

   function Fault_Detected(A, B, C : Float) return Boolean is
      Tolerance : constant Float := 0.01;
      AB_OK : Boolean := abs(A - B) <= Tolerance;
      BC_OK : Boolean := abs(B - C) <= Tolerance;
      AC_OK : Boolean := abs(A - C) <= Tolerance;
   begin
      return not (AB_OK or BC_OK or AC_OK);
   end Fault_Detected;

end TMR_Voter_V2;
