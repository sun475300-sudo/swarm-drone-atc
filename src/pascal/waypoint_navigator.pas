{ Phase 579 — Pascal waypoint navigator program with Haversine distance calculation }
{ SDACS drone waypoint planning and navigation utility }

program WaypointNavigator;

uses
  Math, SysUtils;

const
  EARTH_RADIUS_M = 6371000.0;
  DEG_TO_RAD     = PI / 180.0;
  MAX_WAYPOINTS  = 256;

type
  { Waypoint record representing a 3D navigation point }
  Waypoint = record
    Id       : Integer;
    Name     : string[32];
    Latitude : Double;
    Longitude: Double;
    AltMeters: Double;
    SpeedMps : Double;
  end;

  { Waypoint list type }
  WaypointList = array[1..MAX_WAYPOINTS] of Waypoint;

  { Route containing an ordered list of Waypoint entries }
  Route = record
    Count       : Integer;
    TotalDistM  : Double;
    Points      : WaypointList;
  end;

{ Haversine great-circle distance between two lat/lon coordinates (metres) }
function HaversineDistance(lat1, lon1, lat2, lon2: Double): Double;
var
  dlat, dlon, a, c: Double;
begin
  dlat := (lat2 - lat1) * DEG_TO_RAD;
  dlon := (lon2 - lon1) * DEG_TO_RAD;
  a := sin(dlat / 2) * sin(dlat / 2) +
       cos(lat1 * DEG_TO_RAD) * cos(lat2 * DEG_TO_RAD) *
       sin(dlon / 2) * sin(dlon / 2);
  c := 2 * arctan2(sqrt(a), sqrt(1 - a));
  HaversineDistance := EARTH_RADIUS_M * c;
end;

{ 3D distance including altitude difference }
function Distance3D(const a, b: Waypoint): Double;
var
  groundDist, altDiff: Double;
begin
  groundDist := HaversineDistance(a.Latitude, a.Longitude, b.Latitude, b.Longitude);
  altDiff    := b.AltMeters - a.AltMeters;
  Distance3D := sqrt(groundDist * groundDist + altDiff * altDiff);
end;

{ Add a Waypoint to an existing Route }
procedure AddWaypoint(var r: Route; wp: Waypoint);
begin
  if r.Count >= MAX_WAYPOINTS then
    Exit;
  Inc(r.Count);
  r.Points[r.Count] := wp;
  if r.Count > 1 then
    r.TotalDistM := r.TotalDistM + Distance3D(r.Points[r.Count - 1], r.Points[r.Count]);
end;

{ Print a Waypoint's details }
procedure PrintWaypoint(const wp: Waypoint);
begin
  WriteLn(Format('  [%d] %s  lat=%.6f lon=%.6f alt=%.1fm spd=%.1fm/s',
    [wp.Id, wp.Name, wp.Latitude, wp.Longitude, wp.AltMeters, wp.SpeedMps]));
end;

{ Print full Route summary }
procedure PrintRoute(const r: Route);
var
  i: Integer;
begin
  WriteLn('=== Waypoint Route ===');
  WriteLn(Format('Total waypoints : %d', [r.Count]));
  WriteLn(Format('Total distance  : %.2f m', [r.TotalDistM]));
  for i := 1 to r.Count do
    PrintWaypoint(r.Points[i]);
end;

{ Estimate total flight time for the route at waypoint speeds }
function EstimateFlightTimeSec(const r: Route): Double;
var
  i: Integer;
  segDist, segTime: Double;
begin
  segTime := 0;
  for i := 2 to r.Count do
  begin
    segDist := Distance3D(r.Points[i - 1], r.Points[i]);
    if r.Points[i].SpeedMps > 0 then
      segTime := segTime + segDist / r.Points[i].SpeedMps;
  end;
  EstimateFlightTimeSec := segTime;
end;

{ Main program entry }
var
  route : Route;
  wp    : Waypoint;
  eta   : Double;
begin
  route.Count      := 0;
  route.TotalDistM := 0.0;

  { Build a sample route over the test area }
  wp.Id := 1; wp.Name := 'Launch';    wp.Latitude := 37.4220; wp.Longitude := 127.1275; wp.AltMeters := 50.0;  wp.SpeedMps := 10.0; AddWaypoint(route, wp);
  wp.Id := 2; wp.Name := 'Waypoint1'; wp.Latitude := 37.4230; wp.Longitude := 127.1285; wp.AltMeters := 80.0;  wp.SpeedMps := 12.0; AddWaypoint(route, wp);
  wp.Id := 3; wp.Name := 'Waypoint2'; wp.Latitude := 37.4245; wp.Longitude := 127.1300; wp.AltMeters := 100.0; wp.SpeedMps := 15.0; AddWaypoint(route, wp);
  wp.Id := 4; wp.Name := 'Landing';   wp.Latitude := 37.4260; wp.Longitude := 127.1320; wp.AltMeters := 10.0;  wp.SpeedMps := 5.0;  AddWaypoint(route, wp);

  PrintRoute(route);

  eta := EstimateFlightTimeSec(route);
  WriteLn(Format('Estimated ETA   : %.1f s (%.2f min)', [eta, eta / 60.0]));
end.
