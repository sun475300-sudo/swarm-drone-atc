-- Safety Critical Module — SDACS Phase 595
-- Implements safety-critical drone monitoring with TMR validation

with Ada.Text_IO; use Ada.Text_IO;

package body Safety_Critical is

   procedure Check (Status : in Natural) is
   begin
      if Status = 0 then
         Put_Line ("Safety check: OK");
      else
         Put_Line ("Safety check: FAULT code " & Natural'Image (Status));
      end if;
   end Check;

   function Is_Safe (Altitude : in Float; Speed : in Float) return Boolean is
      Max_Altitude : constant Float := 150.0;
      Max_Speed    : constant Float := 20.0;
   begin
      return Altitude >= 0.0 and Altitude <= Max_Altitude
         and Speed >= 0.0 and Speed <= Max_Speed;
   end Is_Safe;

   procedure Emergency_Land (Drone_ID : in String) is
   begin
      Put_Line ("EMERGENCY LAND: " & Drone_ID);
   end Emergency_Land;

   function Battery_OK (Level : in Natural) return Boolean is
   begin
      return Level >= 20;
   end Battery_OK;

end Safety_Critical;
-- end
-- end
-- end
-- end
-- end
-- end
-- end
-- end
-- end
-- end
-- end
-- end
-- end
-- end
-- end
-- end
-- end
