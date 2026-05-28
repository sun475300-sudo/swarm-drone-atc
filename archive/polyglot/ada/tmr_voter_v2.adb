-- Phase 655: TMR Voter V2 — Ada Triple Modular Redundancy with Byzantine Fault Tolerance
-- 3중 모듈 중복 투표기 v2: 비잔틴 장애 허용

with Ada.Text_IO;           use Ada.Text_IO;
with Ada.Float_Text_IO;     use Ada.Float_Text_IO;

procedure TMR_Voter_V2 is

   type Sensor_Channel is (Channel_A, Channel_B, Channel_C);
   type Sensor_Reading is record
      Value     : Float;
      Valid     : Boolean;
      Timestamp : Natural;
   end record;

   type TMR_Array is array (Sensor_Channel) of Sensor_Reading;

   type Vote_Result is record
      Voted_Value   : Float;
      Confidence    : Float;   -- 0.0 to 1.0
      Agreement     : Natural; -- number of agreeing channels
      Faulty_Channel : Sensor_Channel;
      Has_Fault     : Boolean;
   end record;

   Tolerance : constant Float := 0.5;  -- tolerance for agreement

   function Abs_Val (X : Float) return Float is
   begin
      if X < 0.0 then
         return -X;
      else
         return X;
      end if;
   end Abs_Val;

   function Vote (Readings : TMR_Array) return Vote_Result is
      A : constant Float := Readings (Channel_A).Value;
      B : constant Float := Readings (Channel_B).Value;
      C : constant Float := Readings (Channel_C).Value;

      AB_Agree : constant Boolean := Abs_Val (A - B) < Tolerance;
      BC_Agree : constant Boolean := Abs_Val (B - C) < Tolerance;
      AC_Agree : constant Boolean := Abs_Val (A - C) < Tolerance;

      Result : Vote_Result;
   begin
      Result.Has_Fault := False;
      Result.Faulty_Channel := Channel_A;

      if AB_Agree and BC_Agree and AC_Agree then
         -- All three agree: highest confidence
         Result.Voted_Value := (A + B + C) / 3.0;
         Result.Confidence := 1.0;
         Result.Agreement := 3;

      elsif AB_Agree then
         -- A and B agree, C is faulty
         Result.Voted_Value := (A + B) / 2.0;
         Result.Confidence := 0.67;
         Result.Agreement := 2;
         Result.Has_Fault := True;
         Result.Faulty_Channel := Channel_C;

      elsif BC_Agree then
         -- B and C agree, A is faulty
         Result.Voted_Value := (B + C) / 2.0;
         Result.Confidence := 0.67;
         Result.Agreement := 2;
         Result.Has_Fault := True;
         Result.Faulty_Channel := Channel_A;

      elsif AC_Agree then
         -- A and C agree, B is faulty
         Result.Voted_Value := (A + C) / 2.0;
         Result.Confidence := 0.67;
         Result.Agreement := 2;
         Result.Has_Fault := True;
         Result.Faulty_Channel := Channel_B;

      else
         -- No agreement: use median
         if (A >= B and A <= C) or (A <= B and A >= C) then
            Result.Voted_Value := A;
         elsif (B >= A and B <= C) or (B <= A and B >= C) then
            Result.Voted_Value := B;
         else
            Result.Voted_Value := C;
         end if;
         Result.Confidence := 0.33;
         Result.Agreement := 0;
         Result.Has_Fault := True;
      end if;

      return Result;
   end Vote;

   -- Test scenarios
   type Test_Case is record
      Name : String (1 .. 20);
      R    : TMR_Array;
   end record;

   T1 : constant TMR_Array := (
      Channel_A => (60.0, True, 1),
      Channel_B => (60.1, True, 1),
      Channel_C => (59.9, True, 1));

   T2 : constant TMR_Array := (
      Channel_A => (60.0, True, 2),
      Channel_B => (60.2, True, 2),
      Channel_C => (999.0, True, 2));

   T3 : constant TMR_Array := (
      Channel_A => (60.0, True, 3),
      Channel_B => (120.0, True, 3),
      Channel_C => (999.0, True, 3));

   V : Vote_Result;

begin
   Put_Line ("=== TMR Voter V2: Byzantine Fault Tolerance ===");
   Put_Line ("");

   -- Test 1: All agree
   V := Vote (T1);
   Put ("  Test 1 (all agree):   voted=");
   Put (V.Voted_Value, Fore => 3, Aft => 2, Exp => 0);
   Put ("  conf=");
   Put (V.Confidence, Fore => 1, Aft => 2, Exp => 0);
   Put ("  agree=");
   Put_Line (Natural'Image (V.Agreement));

   -- Test 2: One faulty
   V := Vote (T2);
   Put ("  Test 2 (C faulty):    voted=");
   Put (V.Voted_Value, Fore => 3, Aft => 2, Exp => 0);
   Put ("  conf=");
   Put (V.Confidence, Fore => 1, Aft => 2, Exp => 0);
   Put ("  fault=" & Sensor_Channel'Image (V.Faulty_Channel));
   New_Line;

   -- Test 3: Byzantine (no agreement)
   V := Vote (T3);
   Put ("  Test 3 (byzantine):   voted=");
   Put (V.Voted_Value, Fore => 3, Aft => 2, Exp => 0);
   Put ("  conf=");
   Put (V.Confidence, Fore => 1, Aft => 2, Exp => 0);
   Put_Line ("  agree=0");

   Put_Line ("");
   Put_Line ("=== TMR V2 Complete ===");
end TMR_Voter_V2;
