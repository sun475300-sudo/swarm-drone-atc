-- Phase 655 — Ada TMR Voter v2 (Byzantine fault tolerance)
with Ada.Text_IO; use Ada.Text_IO;

procedure TMR_Voter_V2 is
   type Channel_Value is digits 10;
   type Channel_Array is array (1 .. 3) of Channel_Value;

   function Vote (Channels : Channel_Array; Threshold : Channel_Value := 0.01)
      return Channel_Value is
   begin
      -- Triple Modular Redundancy: majority vote
      for I in Channels'Range loop
         for J in I + 1 .. Channels'Last loop
            if abs (Channels (I) - Channels (J)) <= Threshold then
               return (Channels (I) + Channels (J)) / 2.0;
            end if;
         end loop;
      end loop;
      -- No majority found: return median
      return Channels (2);
   end Vote;

   Values : Channel_Array := (10.001, 10.002, 15.500);  -- One faulty channel
begin
   Put_Line ("Voted value:" & Channel_Value'Image (Vote (Values)));
end TMR_Voter_V2;
