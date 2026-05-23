{
  Phase 579: Waypoint Navigator — Pascal
  웨이포인트 기반 드론 네비게이션.
  경로 계획, 거리/방위 계산, ETA 추정.
}

program WaypointNavigator;

uses
  SysUtils, Math;

const
  MAX_WAYPOINTS = 100;
  EARTH_RADIUS  = 6371000.0;    { 미터 }
  DEG_TO_RAD    = Pi / 180.0;
  RAD_TO_DEG    = 180.0 / Pi;
  DEFAULT_SPEED = 15.0;         { m/s }

type
  { 웨이포인트 레코드 }
  TWaypoint = record
    Id:        Integer;
    Name:      string[32];
    Latitude:  Double;
    Longitude: Double;
    Altitude:  Double;          { 미터 AGL }
    Speed:     Double;          { m/s, 0이면 기본값 }
    Action:    string[16];      { hover, photo, land, pass }
  end;

  { 네비게이션 결과 }
  TNavResult = record
    FromWP:    Integer;
    ToWP:      Integer;
    Distance:  Double;          { 미터 }
    Bearing:   Double;          { 도 }
    ETA:       Double;          { 초 }
    AltChange: Double;          { 미터 }
  end;

  { 드론 상태 }
  TDroneState = record
    Lat:       Double;
    Lon:       Double;
    Alt:       Double;
    Heading:   Double;
    Speed:     Double;
    Battery:   Double;          { 퍼센트 }
    WPIndex:   Integer;
  end;

  { 웨이포인트 배열 }
  TWaypointArray = array[0..MAX_WAYPOINTS-1] of TWaypoint;
  TNavResultArray = array[0..MAX_WAYPOINTS-1] of TNavResult;

var
  Waypoints:     TWaypointArray;
  NavResults:    TNavResultArray;
  WaypointCount: Integer;
  DroneState:    TDroneState;

{ ─── Haversine 거리 계산 ─── }
function HaversineDistance(Lat1, Lon1, Lat2, Lon2: Double): Double;
var
  dLat, dLon, a, c: Double;
begin
  dLat := (Lat2 - Lat1) * DEG_TO_RAD;
  dLon := (Lon2 - Lon1) * DEG_TO_RAD;
  a := Sin(dLat / 2) * Sin(dLat / 2) +
       Cos(Lat1 * DEG_TO_RAD) * Cos(Lat2 * DEG_TO_RAD) *
       Sin(dLon / 2) * Sin(dLon / 2);
  c := 2 * ArcTan2(Sqrt(a), Sqrt(1 - a));
  HaversineDistance := EARTH_RADIUS * c;
end;

{ ─── 방위각 계산 ─── }
function CalculateBearing(Lat1, Lon1, Lat2, Lon2: Double): Double;
var
  dLon, x, y, bearing: Double;
begin
  dLon := (Lon2 - Lon1) * DEG_TO_RAD;
  y := Sin(dLon) * Cos(Lat2 * DEG_TO_RAD);
  x := Cos(Lat1 * DEG_TO_RAD) * Sin(Lat2 * DEG_TO_RAD) -
       Sin(Lat1 * DEG_TO_RAD) * Cos(Lat2 * DEG_TO_RAD) * Cos(dLon);
  bearing := ArcTan2(y, x) * RAD_TO_DEG;
  if bearing < 0 then
    bearing := bearing + 360.0;
  CalculateBearing := bearing;
end;

{ ─── ETA 계산 ─── }
function CalculateETA(Distance, Speed: Double): Double;
begin
  if Speed > 0 then
    CalculateETA := Distance / Speed
  else
    CalculateETA := Distance / DEFAULT_SPEED;
end;

{ ─── 웨이포인트 추가 ─── }
procedure AddWaypoint(Id: Integer; Name: string; Lat, Lon, Alt, Spd: Double; Act: string);
begin
  if WaypointCount < MAX_WAYPOINTS then
  begin
    Waypoints[WaypointCount].Id := Id;
    Waypoints[WaypointCount].Name := Name;
    Waypoints[WaypointCount].Latitude := Lat;
    Waypoints[WaypointCount].Longitude := Lon;
    Waypoints[WaypointCount].Altitude := Alt;
    Waypoints[WaypointCount].Speed := Spd;
    Waypoints[WaypointCount].Action := Act;
    Inc(WaypointCount);
  end;
end;

{ ─── 경로 분석 ─── }
procedure AnalyzeRoute;
var
  i: Integer;
  dist, bearing, eta, altChange: Double;
  totalDist, totalETA: Double;
begin
  totalDist := 0;
  totalETA := 0;

  WriteLn('=== Route Analysis ===');
  WriteLn(Format('%-4s %-12s %-12s %-10s %-8s %-8s',
    ['Leg', 'From', 'To', 'Dist(m)', 'Brg(°)', 'ETA(s)']));
  WriteLn(StringOfChar('-', 60));

  for i := 0 to WaypointCount - 2 do
  begin
    dist := HaversineDistance(
      Waypoints[i].Latitude, Waypoints[i].Longitude,
      Waypoints[i+1].Latitude, Waypoints[i+1].Longitude);
    bearing := CalculateBearing(
      Waypoints[i].Latitude, Waypoints[i].Longitude,
      Waypoints[i+1].Latitude, Waypoints[i+1].Longitude);
    altChange := Waypoints[i+1].Altitude - Waypoints[i].Altitude;
    eta := CalculateETA(dist, Waypoints[i+1].Speed);

    NavResults[i].FromWP := i;
    NavResults[i].ToWP := i + 1;
    NavResults[i].Distance := dist;
    NavResults[i].Bearing := bearing;
    NavResults[i].ETA := eta;
    NavResults[i].AltChange := altChange;

    totalDist := totalDist + dist;
    totalETA := totalETA + eta;

    WriteLn(Format('%-4d %-12s %-12s %-10.1f %-8.1f %-8.1f',
      [i, Waypoints[i].Name, Waypoints[i+1].Name, dist, bearing, eta]));
  end;

  WriteLn(StringOfChar('-', 60));
  WriteLn(Format('Total distance: %.1f m', [totalDist]));
  WriteLn(Format('Total ETA:      %.1f s (%.1f min)', [totalETA, totalETA / 60]));
  WriteLn(Format('Waypoints:      %d', [WaypointCount]));
end;

{ ─── 메인 프로그램 ─── }
begin
  WaypointCount := 0;

  WriteLn('=== SDACS Waypoint Navigator ===');
  WriteLn;

  { 테스트 웨이포인트 (서울 지역) }
  AddWaypoint(0, 'HOME',     37.5665, 126.9780, 0,   0,  'takeoff');
  AddWaypoint(1, 'WP_ALPHA', 37.5700, 126.9750, 100, 15, 'pass');
  AddWaypoint(2, 'WP_BRAVO', 37.5750, 126.9800, 120, 12, 'hover');
  AddWaypoint(3, 'WP_CHARLIE',37.5720, 126.9850, 80, 15, 'photo');
  AddWaypoint(4, 'WP_DELTA', 37.5680, 126.9820, 100, 10, 'pass');
  AddWaypoint(5, 'LANDING',  37.5665, 126.9780, 0,   8,  'land');

  AnalyzeRoute;
end.
