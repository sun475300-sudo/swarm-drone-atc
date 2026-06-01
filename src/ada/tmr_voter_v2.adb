-- TMR (Triple Modular Redundancy) voter v2 — Ada stub for SDACS safety layer
package body TMR_Voter_V2 is

   function Vote (A, B, C : Float) return Float is
   begin
      if abs (A - B) < abs (A - C) then
         return (A + B) / 2.0;
      else
         return (A + C) / 2.0;
      end if;
   end Vote;

   function All_Agree (A, B, C : Float; Tol : Float := 0.01) return Boolean is
   begin
      return abs (A - B) < Tol and then abs (B - C) < Tol;
   end All_Agree;

end TMR_Voter_V2;
