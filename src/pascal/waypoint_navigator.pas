{ waypoint_navigator.pas - Waypoint navigation for SDACS drones }
{ Pascal implementation of drone waypoint path planning }

program WaypointNavigator;

uses
  SysUtils, Math;

type
  TVector3D = record
    X, Y, Z: Double;
  end;

  TWaypoint = record
    ID:        Integer;
    Position:  TVector3D;
    Altitude:  Double;
    Speed:     Double;
    HoldTime:  Integer;
    Reached:   Boolean;
  end;

  TWaypointList = array of TWaypoint;

  TNavigationResult = record
    TotalDistance: Double;
    EstimatedTime: Double;
    WaypointsCount: Integer;
    Success: Boolean;
  end;

{ Compute Haversine great-circle distance between two GPS points }
function HaversineDistance(Lat1, Lon1, Lat2, Lon2: Double): Double;
const
  R = 6371000.0;  { Earth radius in meters }
var
  DLat, DLon, A, C: Double;
begin
  DLat := DegToRad(Lat2 - Lat1);
  DLon := DegToRad(Lon2 - Lon1);
  A := Sin(DLat/2) * Sin(DLat/2) +
       Cos(DegToRad(Lat1)) * Cos(DegToRad(Lat2)) *
       Sin(DLon/2) * Sin(DLon/2);
  C := 2 * ArcTan2(Sqrt(A), Sqrt(1-A));
  Result := R * C;
end;

{ Calculate bearing between two GPS points }
function CalculateBearing(Lat1, Lon1, Lat2, Lon2: Double): Double;
var
  DLon, X, Y: Double;
begin
  DLon := DegToRad(Lon2 - Lon1);
  X := Cos(DegToRad(Lat2)) * Sin(DLon);
  Y := Cos(DegToRad(Lat1)) * Sin(DegToRad(Lat2)) -
       Sin(DegToRad(Lat1)) * Cos(DegToRad(Lat2)) * Cos(DLon);
  Result := RadToDeg(ArcTan2(X, Y));
  if Result < 0 then Result := Result + 360;
end;

{ Create a new Waypoint record }
function CreateWaypoint(ID: Integer; X, Y, Z, Speed: Double): TWaypoint;
begin
  Result.ID := ID;
  Result.Position.X := X;
  Result.Position.Y := Y;
  Result.Position.Z := Z;
  Result.Altitude := Z;
  Result.Speed := Speed;
  Result.HoldTime := 0;
  Result.Reached := False;
end;

{ Calculate total path distance through waypoints }
function CalculatePathDistance(const Waypoints: TWaypointList): Double;
var
  I: Integer;
  DX, DY, DZ, SegDist: Double;
begin
  Result := 0;
  for I := 0 to High(Waypoints) - 1 do
  begin
    DX := Waypoints[I+1].Position.X - Waypoints[I].Position.X;
    DY := Waypoints[I+1].Position.Y - Waypoints[I].Position.Y;
    DZ := Waypoints[I+1].Position.Z - Waypoints[I].Position.Z;
    SegDist := Sqrt(DX*DX + DY*DY + DZ*DZ);
    Result := Result + SegDist;
  end;
end;

{ Navigate through waypoint list }
function NavigateWaypoints(var Waypoints: TWaypointList; Speed: Double): TNavigationResult;
var
  I: Integer;
  Distance: Double;
begin
  Result.WaypointsCount := Length(Waypoints);
  Result.TotalDistance := CalculatePathDistance(Waypoints);
  if Speed > 0 then
    Result.EstimatedTime := Result.TotalDistance / Speed
  else
    Result.EstimatedTime := 0;

  for I := 0 to High(Waypoints) do
    Waypoints[I].Reached := True;

  Result.Success := True;
end;

var
  WaypointList: TWaypointList;
  NavResult: TNavigationResult;
begin
  WriteLn('SDACS Waypoint Navigator');
  WriteLn('========================');

  SetLength(WaypointList, 4);
  WaypointList[0] := CreateWaypoint(1, 0.0,    0.0,    50.0, 15.0);
  WaypointList[1] := CreateWaypoint(2, 500.0,  200.0,  80.0, 15.0);
  WaypointList[2] := CreateWaypoint(3, 1000.0, 500.0, 100.0, 12.0);
  WaypointList[3] := CreateWaypoint(4, 800.0,  800.0,  60.0, 10.0);

  NavResult := NavigateWaypoints(WaypointList, 15.0);
  WriteLn(Format('Waypoints: %d', [NavResult.WaypointsCount]));
  WriteLn(Format('Total Distance: %.1f m', [NavResult.TotalDistance]));
  WriteLn(Format('Estimated Time: %.1f s', [NavResult.EstimatedTime]));
  WriteLn(Format('Success: %s', [BoolToStr(NavResult.Success, True)]));
end.
