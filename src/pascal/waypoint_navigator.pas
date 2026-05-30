{ Phase 579: waypoint_navigator — Pascal 기반 웨이포인트 항법 }
{ SDACS Waypoint Navigator with Haversine Distance Calculation }

program WaypointNavigator;

uses
  SysUtils, Math;

const
  EARTH_RADIUS = 6371000.0;  { 지구 반경 (m) }
  MAX_WAYPOINTS = 50;
  DEG_TO_RAD = Pi / 180.0;

type
  { 웨이포인트 레코드 }
  TWaypoint = record
    Id       : Integer;
    Lat      : Double;
    Lon      : Double;
    Alt      : Double;
    Name     : String;
    Speed    : Double;  { 목표 속도 m/s }
  end;

  { 드론 항법 상태 }
  TNavigationState = record
    CurrentLat   : Double;
    CurrentLon   : Double;
    CurrentAlt   : Double;
    Heading      : Double;
    Speed        : Double;
    WaypointIdx  : Integer;
    TotalDist    : Double;
    Completed    : Boolean;
  end;

  TWaypointArray = array[0..MAX_WAYPOINTS - 1] of TWaypoint;

{ Haversine 거리 계산 }
function HaversineDistance(Lat1, Lon1, Lat2, Lon2: Double): Double;
var
  dLat, dLon, a, c: Double;
begin
  dLat := (Lat2 - Lat1) * DEG_TO_RAD;
  dLon := (Lon2 - Lon1) * DEG_TO_RAD;
  a := Sin(dLat / 2) * Sin(dLat / 2) +
       Cos(Lat1 * DEG_TO_RAD) * Cos(Lat2 * DEG_TO_RAD) *
       Sin(dLon / 2) * Sin(dLon / 2);
  c := 2.0 * ArcTan2(Sqrt(a), Sqrt(1.0 - a));
  Result := EARTH_RADIUS * c;
end;

{ 방위각 계산 }
function ComputeBearing(Lat1, Lon1, Lat2, Lon2: Double): Double;
var
  dLon, y, x: Double;
begin
  dLon := (Lon2 - Lon1) * DEG_TO_RAD;
  y := Sin(dLon) * Cos(Lat2 * DEG_TO_RAD);
  x := Cos(Lat1 * DEG_TO_RAD) * Sin(Lat2 * DEG_TO_RAD) -
       Sin(Lat1 * DEG_TO_RAD) * Cos(Lat2 * DEG_TO_RAD) * Cos(dLon);
  Result := ArcTan2(y, x) / DEG_TO_RAD;
  if Result < 0.0 then
    Result := Result + 360.0;
end;

{ 웨이포인트 경로 전체 거리 계산 }
function ComputeRouteDistance(const Waypoints: TWaypointArray; Count: Integer): Double;
var
  i: Integer;
  Total: Double;
begin
  Total := 0.0;
  for i := 0 to Count - 2 do
    Total := Total + HaversineDistance(
      Waypoints[i].Lat, Waypoints[i].Lon,
      Waypoints[i+1].Lat, Waypoints[i+1].Lon
    );
  Result := Total;
end;

{ 항법 단계 실행 (단순 시뮬레이션) }
procedure NavigateStep(var State: TNavigationState;
                       const Waypoints: TWaypointArray; Count: Integer;
                       dt: Double);
var
  Target: TWaypoint;
  Dist, Bearing: Double;
  MoveAlt: Double;
begin
  if State.Completed or (State.WaypointIdx >= Count) then
  begin
    State.Completed := True;
    Exit;
  end;

  Target := Waypoints[State.WaypointIdx];
  Dist := HaversineDistance(State.CurrentLat, State.CurrentLon,
                             Target.Lat, Target.Lon);
  Bearing := ComputeBearing(State.CurrentLat, State.CurrentLon,
                              Target.Lat, Target.Lon);

  if Dist < 2.0 then
  begin
    { 웨이포인트 도달 }
    State.CurrentLat := Target.Lat;
    State.CurrentLon := Target.Lon;
    State.CurrentAlt := Target.Alt;
    State.WaypointIdx := State.WaypointIdx + 1;
    if State.WaypointIdx >= Count then
      State.Completed := True;
  end
  else
  begin
    { 웨이포인트 방향으로 이동 }
    State.Speed := Target.Speed;
    State.Heading := Bearing;
    MoveAlt := Target.Alt - State.CurrentAlt;
    State.CurrentAlt := State.CurrentAlt + MoveAlt * dt * 0.5;
    State.TotalDist := State.TotalDist + State.Speed * dt;
  end;
end;

{ 항법 보고서 출력 }
procedure PrintNavReport(const State: TNavigationState; Step: Integer);
begin
  WriteLn(Format('  스텝 %d: lat=%.4f lon=%.4f alt=%.1fm heading=%.1f° wp=%d',
    [Step, State.CurrentLat, State.CurrentLon, State.CurrentAlt,
     State.Heading, State.WaypointIdx]));
end;

{ 메인 프로그램 }
var
  Waypoints: TWaypointArray;
  WpCount: Integer;
  State: TNavigationState;
  i: Integer;
  TotalDist: Double;

begin
  WriteLn('SDACS Waypoint Navigator — Phase 579');
  WriteLn;

  { 웨이포인트 정의 }
  WpCount := 5;
  Waypoints[0] := (Id: 0; Lat: 37.500; Lon: 127.000; Alt: 50.0; Name: 'Home'; Speed: 5.0);
  Waypoints[1] := (Id: 1; Lat: 37.502; Lon: 127.002; Alt: 60.0; Name: 'WP1';  Speed: 8.0);
  Waypoints[2] := (Id: 2; Lat: 37.505; Lon: 127.005; Alt: 70.0; Name: 'WP2';  Speed: 8.0);
  Waypoints[3] := (Id: 3; Lat: 37.508; Lon: 127.003; Alt: 55.0; Name: 'WP3';  Speed: 6.0);
  Waypoints[4] := (Id: 4; Lat: 37.505; Lon: 127.001; Alt: 50.0; Name: 'RTL';  Speed: 5.0);

  { 총 경로 거리 계산 (Haversine) }
  TotalDist := ComputeRouteDistance(Waypoints, WpCount);
  WriteLn(Format('총 경로 거리: %.1fm', [TotalDist]));
  WriteLn(Format('웨이포인트 수: %d개', [WpCount]));
  WriteLn;

  { 초기 상태 설정 }
  State.CurrentLat  := Waypoints[0].Lat;
  State.CurrentLon  := Waypoints[0].Lon;
  State.CurrentAlt  := Waypoints[0].Alt;
  State.Heading     := 0.0;
  State.Speed       := 0.0;
  State.WaypointIdx := 1;  { 첫 번째 웨이포인트로 이동 }
  State.TotalDist   := 0.0;
  State.Completed   := False;

  WriteLn('항법 시뮬레이션:');
  for i := 1 to 10 do
  begin
    NavigateStep(State, Waypoints, WpCount, 1.0);
    PrintNavReport(State, i);
    if State.Completed then Break;
  end;

  WriteLn;
  WriteLn('웨이포인트 항법 완료.');
end.
