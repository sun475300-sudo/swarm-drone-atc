{ Waypoint Navigator — Pascal for SDACS autonomous navigation }
{ Phase 579 }
program WaypointNavigator;

uses
  Math, SysUtils;

type
  TCoordinate = record
    Latitude  : Double;
    Longitude : Double;
    Altitude  : Double;
  end;

  Waypoint = record
    ID       : String;
    Position : TCoordinate;
    Radius   : Double;   { acceptance radius in meters }
  end;

  TWaypointList = array of Waypoint;

{ Haversine distance between two GPS coordinates (meters) }
function Haversine(A, B: TCoordinate): Double;
const
  R = 6371000.0;
var
  dLat, dLon, sinDLat, sinDLon, Calc: Double;
begin
  dLat := DegToRad(B.Latitude  - A.Latitude);
  dLon := DegToRad(B.Longitude - A.Longitude);
  sinDLat := Sin(dLat / 2);
  sinDLon := Sin(dLon / 2);
  Calc := sinDLat*sinDLat +
          Cos(DegToRad(A.Latitude)) * Cos(DegToRad(B.Latitude)) *
          sinDLon * sinDLon;
  Result := 2 * R * ArcTan2(Sqrt(Calc), Sqrt(1 - Calc));
end;

{ Bearing from A to B in degrees (0=North, 90=East) }
function Bearing(A, B: TCoordinate): Double;
var
  dLon, x, y: Double;
begin
  dLon := DegToRad(B.Longitude - A.Longitude);
  y := Sin(dLon) * Cos(DegToRad(B.Latitude));
  x := Cos(DegToRad(A.Latitude)) * Sin(DegToRad(B.Latitude)) -
       Sin(DegToRad(A.Latitude)) * Cos(DegToRad(B.Latitude)) * Cos(dLon);
  Result := RadToDeg(ArcTan2(y, x));
  if Result < 0 then Result := Result + 360.0;
end;

{ Simple navigator: returns next Waypoint index and bearing }
function Navigate(Current: TCoordinate; Waypoints: TWaypointList; CurrentWP: Integer): Integer;
var
  Dist: Double;
begin
  Result := CurrentWP;
  if Length(Waypoints) = 0 then Exit;
  if CurrentWP >= Length(Waypoints) then Exit;

  Dist := Haversine(Current, Waypoints[CurrentWP].Position);
  if Dist <= Waypoints[CurrentWP].Radius then
    Result := CurrentWP + 1;  { advance to next Waypoint }
end;

var
  WPList  : TWaypointList;
  CurrentPos : TCoordinate;
  i       : Integer;
begin
  { Example mission: 4 Waypoints around Seoul }
  SetLength(WPList, 4);
  WPList[0].ID := 'WP-001'; WPList[0].Position.Latitude := 37.5665; WPList[0].Position.Longitude := 126.9780; WPList[0].Radius := 10.0;
  WPList[1].ID := 'WP-002'; WPList[1].Position.Latitude := 37.5700; WPList[1].Position.Longitude := 126.9800; WPList[1].Radius := 10.0;
  WPList[2].ID := 'WP-003'; WPList[2].Position.Latitude := 37.5720; WPList[2].Position.Longitude := 126.9820; WPList[2].Radius := 10.0;
  WPList[3].ID := 'WP-004'; WPList[3].Position.Latitude := 37.5740; WPList[3].Position.Longitude := 126.9840; WPList[3].Radius := 10.0;

  CurrentPos.Latitude := 37.5665; CurrentPos.Longitude := 126.9780; CurrentPos.Altitude := 100.0;

  WriteLn('Waypoint Navigator started with ', Length(WPList), ' waypoints.');
  for i := 0 to High(WPList) do begin
    WriteLn('  ', WPList[i].ID, ' dist=',
            Haversine(CurrentPos, WPList[i].Position):6:1, 'm',
            ' bearing=', Bearing(CurrentPos, WPList[i].Position):6:1, 'deg');
  end;
end.
