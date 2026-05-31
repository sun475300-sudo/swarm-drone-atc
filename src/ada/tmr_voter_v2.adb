-- TMR Voter v2 — SDACS Phase 657
package body TMR_Voter_V2 is
   procedure Vote (A, B, C : in Integer; Result : out Integer) is
   begin
      if A = B then Result := A;
      elsif B = C then Result := B;
      else Result := A;
      end if;
   end Vote;
end TMR_Voter_V2;
