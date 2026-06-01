{
  Phase 579: Waypoint Navigator — 드론 웨이포인트 항법 (Pascal)
  Haversine-based waypoint navigation for drone route planning.
}
program WaypointNavigator;

uses Math, SysUtils;

const
  PHASE        = 579;
  EARTH_RADIUS = 6371000.0;  { Earth radius in metres }

type
  TWaypoint = record
    Id        : Integer;
    Latitude  : Double;   { degrees }
    Longitude : Double;   { degrees }
    Altitude  : Double;   { metres AGL }
    Name      : String;
  end;

  TWaypointArray = array of TWaypoint;

  TNavigationPlan = record
    DroneId     : Integer;
    Waypoints   : TWaypointArray;
    TotalDist   : Double;   { metres }
    ETA_seconds : Double;
  end;

{ ── Haversine great-circle distance ─────────────────────────────── }
function HaversineDistance(Lat1, Lon1, Lat2, Lon2: Double): Double;
var
  dLat, dLon, a, c: Double;
  Lat1R, Lat2R: Double;
begin
  Lat1R := Lat1 * Pi / 180.0;
  Lat2R := Lat2 * Pi / 180.0;
  dLat  := (Lat2 - Lat1) * Pi / 180.0;
  dLon  := (Lon2 - Lon1) * Pi / 180.0;
  a := Sin(dLat/2) * Sin(dLat/2) +
       Cos(Lat1R) * Cos(Lat2R) *
       Sin(dLon/2) * Sin(dLon/2);
  c := 2.0 * ArcTan2(Sqrt(a), Sqrt(1.0 - a));
  HaversineDistance := EARTH_RADIUS * c;
end;

{ ── Bearing computation ─────────────────────────────────────────── }
function BearingDeg(Lat1, Lon1, Lat2, Lon2: Double): Double;
var
  dLon, Lat1R, Lat2R, y, x: Double;
begin
  Lat1R := Lat1 * Pi / 180.0;
  Lat2R := Lat2 * Pi / 180.0;
  dLon  := (Lon2 - Lon1) * Pi / 180.0;
  y := Sin(dLon) * Cos(Lat2R);
  x := Cos(Lat1R) * Sin(Lat2R) - Sin(Lat1R) * Cos(Lat2R) * Cos(dLon);
  BearingDeg := ArcTan2(y, x) * 180.0 / Pi;
  if BearingDeg < 0 then BearingDeg := BearingDeg + 360.0;
end;

{ ── Build navigation plan ───────────────────────────────────────── }
function BuildNavPlan(DroneId: Integer; WPs: TWaypointArray; AvgSpeed: Double): TNavigationPlan;
var
  Plan: TNavigationPlan;
  i:    Integer;
  Dist: Double;
begin
  Plan.DroneId   := DroneId;
  Plan.Waypoints := WPs;
  Plan.TotalDist := 0.0;
  for i := 0 to High(WPs) - 1 do
  begin
    Dist := HaversineDistance(WPs[i].Latitude, WPs[i].Longitude,
                               WPs[i+1].Latitude, WPs[i+1].Longitude);
    Plan.TotalDist := Plan.TotalDist + Dist;
  end;
  if AvgSpeed > 0 then
    Plan.ETA_seconds := Plan.TotalDist / AvgSpeed
  else
    Plan.ETA_seconds := 0;
  BuildNavPlan := Plan;
end;

{ ── Entry point ─────────────────────────────────────────────────── }
var
  WPs:  TWaypointArray;
  Plan: TNavigationPlan;
  i:    Integer;
  d:    Double;

begin
  WriteLn('Phase ' + IntToStr(PHASE) + ': Waypoint Navigator — 드론 웨이포인트 항법');
  WriteLn('Haversine great-circle navigation for drone fleet');

  SetLength(WPs, 4);
  WPs[0].Id := 1; WPs[0].Latitude := 37.5000; WPs[0].Longitude := 127.0000; WPs[0].Altitude := 50; WPs[0].Name := 'HOME';
  WPs[1].Id := 2; WPs[1].Latitude := 37.5050; WPs[1].Longitude := 127.0050; WPs[1].Altitude := 80; WPs[1].Name := 'WP1';
  WPs[2].Id := 3; WPs[2].Latitude := 37.5100; WPs[2].Longitude := 127.0100; WPs[2].Altitude := 80; WPs[2].Name := 'WP2';
  WPs[3].Id := 4; WPs[3].Latitude := 37.5150; WPs[3].Longitude := 127.0150; WPs[3].Altitude := 50; WPs[3].Name := 'BASE';

  Plan := BuildNavPlan(1, WPs, 10.0);
  WriteLn(Format('Total distance:  %.1f m', [Plan.TotalDist]));
  WriteLn(Format('ETA @ 10 m/s:    %.1f s', [Plan.ETA_seconds]));

  for i := 0 to High(WPs) - 1 do
  begin
    d := HaversineDistance(WPs[i].Latitude, WPs[i].Longitude,
                           WPs[i+1].Latitude, WPs[i+1].Longitude);
    WriteLn(Format('  %s -> %s: %.1f m, bearing=%.1f deg',
      [WPs[i].Name, WPs[i+1].Name, d,
       BearingDeg(WPs[i].Latitude, WPs[i].Longitude, WPs[i+1].Latitude, WPs[i+1].Longitude)]));
  end;
  WriteLn('Navigation plan complete — Phase ' + IntToStr(PHASE));
end.
