{ SDACS Waypoint Navigator — Pascal }
{ 군집드론 경유점 항법 모듈 }

program WaypointNavigator;

uses
  Math, SysUtils;

const
  EARTH_RADIUS = 6371000.0;  { 지구 반지름 (미터) }
  MAX_WAYPOINTS = 256;
  DEG_TO_RAD = Pi / 180.0;

type
  Waypoint = record
    lat: Double;
    lon: Double;
    alt: Double;
    name: String;
    reached: Boolean;
  end;

  WaypointList = record
    points: array[0..MAX_WAYPOINTS-1] of Waypoint;
    count: Integer;
    currentIndex: Integer;
  end;

{ Haversine 공식으로 두 좌표 간 거리 계산 }
function Haversine(lat1, lon1, lat2, lon2: Double): Double;
var
  dLat, dLon, a, c: Double;
begin
  dLat := (lat2 - lat1) * DEG_TO_RAD;
  dLon := (lon2 - lon1) * DEG_TO_RAD;
  a := Sin(dLat / 2) * Sin(dLat / 2) +
       Cos(lat1 * DEG_TO_RAD) * Cos(lat2 * DEG_TO_RAD) *
       Sin(dLon / 2) * Sin(dLon / 2);
  c := 2 * ArcTan2(Sqrt(a), Sqrt(1 - a));
  Result := EARTH_RADIUS * c;
end;

{ 경유점 목록 초기화 }
procedure InitWaypointList(var wl: WaypointList);
begin
  wl.count := 0;
  wl.currentIndex := 0;
end;

{ 경유점 추가 }
procedure AddWaypoint(var wl: WaypointList; lat, lon, alt: Double; name: String);
begin
  if wl.count < MAX_WAYPOINTS then
  begin
    wl.points[wl.count].lat := lat;
    wl.points[wl.count].lon := lon;
    wl.points[wl.count].alt := alt;
    wl.points[wl.count].name := name;
    wl.points[wl.count].reached := False;
    Inc(wl.count);
  end;
end;

{ 다음 경유점까지 거리 계산 }
function DistanceToNext(const wl: WaypointList; currentLat, currentLon: Double): Double;
var
  next: Waypoint;
begin
  if wl.currentIndex < wl.count then
  begin
    next := wl.points[wl.currentIndex];
    Result := Haversine(currentLat, currentLon, next.lat, next.lon);
  end
  else
    Result := -1.0;
end;

var
  mission: WaypointList;
  dist: Double;

begin
  WriteLn('SDACS Waypoint Navigator 초기화');
  InitWaypointList(mission);

  AddWaypoint(mission, 37.5665, 126.9780, 100.0, 'Seoul Base');
  AddWaypoint(mission, 37.5700, 126.9800, 120.0, 'Checkpoint Alpha');
  AddWaypoint(mission, 37.5750, 126.9850, 150.0, 'Checkpoint Bravo');
  AddWaypoint(mission, 37.5800, 126.9900, 100.0, 'Target Zone');

  WriteLn('경유점 수: ', mission.count);
  dist := DistanceToNext(mission, 37.5665, 126.9780);
  WriteLn('첫 번째 경유점까지 거리: ', dist:0:2, ' m');
  WriteLn('항법 시스템 준비 완료');
end.
