{ P579: WaypointNavigator - Pascal waypoint navigation for drone fleets }
{ Phase 579: Haversine-based great-circle navigation for GPS waypoints }

program WaypointNavigator;

uses
  Math, SysUtils;

const
  EARTH_RADIUS_M = 6371000.0;
  DEG_TO_RAD     = Pi / 180.0;
  RAD_TO_DEG     = 180.0 / Pi;
  MIN_ALT        = 30.0;
  MAX_ALT        = 150.0;

type
  TGeoPoint = record
    Lat, Lon, Alt: Double;
  end;

  TWaypoint = record
    Id:       String;
    Position: TGeoPoint;
    Speed:    Double;
    Loiter:   Integer;  { seconds to loiter }
    Action:   String;
  end;

  TFlightPlan = record
    Waypoints: array of TWaypoint;
    TotalDistance: Double;
    EstimatedTime: Double;
  end;

{ Haversine formula: distance between two geo-coordinates in meters }
function HaversineDistance(const A, B: TGeoPoint): Double;
var
  dLat, dLon, aVal, cVal: Double;
begin
  dLat := (B.Lat - A.Lat) * DEG_TO_RAD;
  dLon := (B.Lon - A.Lon) * DEG_TO_RAD;
  aVal := Sin(dLat/2)*Sin(dLat/2) +
          Cos(A.Lat*DEG_TO_RAD)*Cos(B.Lat*DEG_TO_RAD)*
          Sin(dLon/2)*Sin(dLon/2);
  cVal := 2 * ArcTan2(Sqrt(aVal), Sqrt(1-aVal));
  Result := EARTH_RADIUS_M * cVal;
end;

{ Bearing from point A to point B in degrees }
function Bearing(const A, B: TGeoPoint): Double;
var
  dLon, x, y: Double;
begin
  dLon := (B.Lon - A.Lon) * DEG_TO_RAD;
  y := Sin(dLon) * Cos(B.Lat*DEG_TO_RAD);
  x := Cos(A.Lat*DEG_TO_RAD)*Sin(B.Lat*DEG_TO_RAD) -
       Sin(A.Lat*DEG_TO_RAD)*Cos(B.Lat*DEG_TO_RAD)*Cos(dLon);
  Result := ArcTan2(y, x) * RAD_TO_DEG;
  if Result < 0 then Result := Result + 360.0;
end;

{ Validate waypoint altitude constraints }
function ValidateWaypoint(const WP: TWaypoint): Boolean;
begin
  Result := (WP.Position.Alt >= MIN_ALT) and (WP.Position.Alt <= MAX_ALT);
end;

{ Build a flight plan from a list of waypoints }
function BuildFlightPlan(const WPList: array of TWaypoint; Speed: Double): TFlightPlan;
var
  i: Integer;
  TotalDist: Double;
begin
  SetLength(Result.Waypoints, Length(WPList));
  for i := 0 to High(WPList) do
    Result.Waypoints[i] := WPList[i];

  TotalDist := 0.0;
  for i := 0 to High(WPList) - 1 do
    TotalDist := TotalDist + HaversineDistance(WPList[i].Position, WPList[i+1].Position);

  Result.TotalDistance  := TotalDist;
  Result.EstimatedTime  := TotalDist / Speed;
end;

{ Main program }
var
  WP1, WP2, WP3: TWaypoint;
  Plan: TFlightPlan;
  Dist: Double;

begin
  WriteLn('WaypointNavigator P579 — SDACS Fleet Navigation');
  WriteLn('================================================');

  WP1.Id := 'HOME';     WP1.Position.Lat := 37.5; WP1.Position.Lon := 127.0; WP1.Position.Alt := 60.0;
  WP2.Id := 'WP_A';    WP2.Position.Lat := 37.51; WP2.Position.Lon := 127.01; WP2.Position.Alt := 80.0;
  WP3.Id := 'TARGET';  WP3.Position.Lat := 37.52; WP3.Position.Lon := 127.02; WP3.Position.Alt := 60.0;

  Dist := HaversineDistance(WP1.Position, WP2.Position);
  WriteLn(Format('Distance HOME -> WP_A: %.1f m', [Dist]));
  WriteLn(Format('Bearing HOME -> WP_A: %.1f deg', [Bearing(WP1.Position, WP2.Position)]));

  Plan := BuildFlightPlan([WP1, WP2, WP3], 15.0);
  WriteLn(Format('Total distance: %.1f m', [Plan.TotalDistance]));
  WriteLn(Format('Estimated time: %.1f s', [Plan.EstimatedTime]));
end.
