{
  Phase 579: Waypoint Navigator — Pascal/Free Pascal
  SDACS autonomous waypoint navigation using Haversine geodesy
}
program WaypointNavigator;

uses
  Math, SysUtils;

const
  EARTH_RADIUS_M  = 6371000.0;
  DEG_TO_RAD      = Pi / 180.0;
  RAD_TO_DEG      = 180.0 / Pi;
  MAX_WAYPOINTS   = 256;
  ARRIVAL_RADIUS  = 5.0;  { meters }

type
  TWaypoint = record
    Id        : Integer;
    Latitude  : Double;
    Longitude : Double;
    Altitude  : Double;
    Speed     : Double;
    Loiter    : Boolean;
    LoiterSec : Integer;
  end;

  TMissionPlan = record
    Name      : string[64];
    Count     : Integer;
    Points    : array[0..MAX_WAYPOINTS - 1] of TWaypoint;
    HomeIndex : Integer;
  end;

  TNavigatorState = record
    CurrentIndex : Integer;
    Reached      : Boolean;
    DistanceToWP : Double;
    BearingToWP  : Double;
    CrossTrackErr: Double;
    MissionDone  : Boolean;
  end;

{ Haversine distance between two lat/lon points in meters }
function Haversine(Lat1, Lon1, Lat2, Lon2: Double): Double;
var
  DLat, DLon, A, C: Double;
begin
  DLat := (Lat2 - Lat1) * DEG_TO_RAD;
  DLon := (Lon2 - Lon1) * DEG_TO_RAD;
  A := Sin(DLat / 2) * Sin(DLat / 2) +
       Cos(Lat1 * DEG_TO_RAD) * Cos(Lat2 * DEG_TO_RAD) *
       Sin(DLon / 2) * Sin(DLon / 2);
  C := 2 * ArcTan2(Sqrt(A), Sqrt(1 - A));
  Result := EARTH_RADIUS_M * C;
end;

{ Initial bearing from point 1 to point 2 in degrees }
function InitialBearing(Lat1, Lon1, Lat2, Lon2: Double): Double;
var
  DLon, X, Y: Double;
begin
  DLon := (Lon2 - Lon1) * DEG_TO_RAD;
  Y := Sin(DLon) * Cos(Lat2 * DEG_TO_RAD);
  X := Cos(Lat1 * DEG_TO_RAD) * Sin(Lat2 * DEG_TO_RAD) -
       Sin(Lat1 * DEG_TO_RAD) * Cos(Lat2 * DEG_TO_RAD) * Cos(DLon);
  Result := ArcTan2(Y, X) * RAD_TO_DEG;
  if Result < 0 then
    Result := Result + 360.0;
end;

{ Cross-track error in meters (negative = left of track) }
function CrossTrackError(Lat1, Lon1, Lat2, Lon2, LatP, LonP: Double): Double;
var
  D13, Theta13, Theta12: Double;
begin
  D13 := Haversine(Lat1, Lon1, LatP, LonP) / EARTH_RADIUS_M;
  Theta13 := InitialBearing(Lat1, Lon1, LatP, LonP) * DEG_TO_RAD;
  Theta12 := InitialBearing(Lat1, Lon1, Lat2, Lon2) * DEG_TO_RAD;
  Result := ArcSin(Sin(D13) * Sin(Theta13 - Theta12)) * EARTH_RADIUS_M;
end;

{ Initialize a waypoint }
function MakeWaypoint(Id: Integer; Lat, Lon, Alt, Spd: Double;
                      Loiter: Boolean; LoiterSec: Integer): TWaypoint;
begin
  Result.Id        := Id;
  Result.Latitude  := Lat;
  Result.Longitude := Lon;
  Result.Altitude  := Alt;
  Result.Speed     := Spd;
  Result.Loiter    := Loiter;
  Result.LoiterSec := LoiterSec;
end;

{ Navigator update: returns next waypoint action }
function UpdateNavigator(var State: TNavigatorState;
                         const Plan: TMissionPlan;
                         CurLat, CurLon, CurAlt: Double): TNavigatorState;
var
  WP: TWaypoint;
begin
  if State.MissionDone or (Plan.Count = 0) then
  begin
    State.MissionDone := True;
    Result := State;
    Exit;
  end;

  WP := Plan.Points[State.CurrentIndex];
  State.DistanceToWP := Haversine(CurLat, CurLon, WP.Latitude, WP.Longitude);
  State.BearingToWP  := InitialBearing(CurLat, CurLon, WP.Latitude, WP.Longitude);

  if State.CurrentIndex > 0 then
  begin
    var Prev := Plan.Points[State.CurrentIndex - 1];
    State.CrossTrackErr := CrossTrackError(
      Prev.Latitude, Prev.Longitude,
      WP.Latitude, WP.Longitude,
      CurLat, CurLon
    );
  end;

  State.Reached := State.DistanceToWP < ARRIVAL_RADIUS;

  if State.Reached and (State.CurrentIndex < Plan.Count - 1) then
  begin
    State.CurrentIndex := State.CurrentIndex + 1;
    State.Reached := False;
  end
  else if State.Reached and (State.CurrentIndex = Plan.Count - 1) then
    State.MissionDone := True;

  Result := State;
end;

{ Main demo }
var
  Plan  : TMissionPlan;
  State : TNavigatorState;
begin
  Plan.Name      := 'Demo Mission';
  Plan.Count     := 3;
  Plan.HomeIndex := 0;

  Plan.Points[0] := MakeWaypoint(0, 37.5665, 126.9780, 50.0, 10.0, False, 0);
  Plan.Points[1] := MakeWaypoint(1, 37.5700, 126.9800, 60.0, 10.0, True,  5);
  Plan.Points[2] := MakeWaypoint(2, 37.5665, 126.9780, 10.0, 5.0,  False, 0);

  State.CurrentIndex := 0;
  State.MissionDone  := False;
  State.Reached      := False;

  WriteLn('Waypoint Navigator initialized.');
  WriteLn('Mission: ', Plan.Name);
  WriteLn('Waypoints: ', Plan.Count);

  State := UpdateNavigator(State, Plan, 37.5666, 126.9781, 45.0);
  WriteLn(Format('Distance to WP0: %.1f m', [State.DistanceToWP]));
  WriteLn(Format('Bearing to WP0: %.1f deg', [State.BearingToWP]));
end.
