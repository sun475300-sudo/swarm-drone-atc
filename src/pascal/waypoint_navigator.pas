{ Waypoint Navigator — SDACS Phase 579 }
{ Drone waypoint navigation with Haversine distance calculation }
program WaypointNavigator;

uses
  Math, SysUtils;

const
  EARTH_RADIUS = 6371000.0;  { meters }

type
  TWaypoint = record
    Lat: Double;
    Lon: Double;
    Alt: Double;
    Name: String;
  end;

  TWaypointList = array of TWaypoint;

function DegToRad(Deg: Double): Double;
begin
  Result := Deg * Pi / 180.0;
end;

function Haversine(W1, W2: TWaypoint): Double;
var
  dLat, dLon, A, C: Double;
begin
  dLat := DegToRad(W2.Lat - W1.Lat);
  dLon := DegToRad(W2.Lon - W1.Lon);
  A := Sin(dLat/2) * Sin(dLat/2) +
       Cos(DegToRad(W1.Lat)) * Cos(DegToRad(W2.Lat)) *
       Sin(dLon/2) * Sin(dLon/2);
  C := 2 * ArcTan2(Sqrt(A), Sqrt(1-A));
  Result := EARTH_RADIUS * C;
end;

function CreateWaypoint(ALat, ALon, AAlt: Double; AName: String): TWaypoint;
begin
  Result.Lat  := ALat;
  Result.Lon  := ALon;
  Result.Alt  := AAlt;
  Result.Name := AName;
end;

var
  WP1, WP2: TWaypoint;
  Dist: Double;
begin
  WP1 := CreateWaypoint(35.1595, 126.8526, 100.0, 'Base');
  WP2 := CreateWaypoint(35.1700, 126.8600, 150.0, 'Target');
  Dist := Haversine(WP1, WP2);
  WriteLn(Format('Distance: %.2f meters', [Dist]));
end.
