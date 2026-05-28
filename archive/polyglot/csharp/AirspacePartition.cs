/// <summary>
/// SDACS 공역 분할 관리자 — C#
/// ================================
/// Voronoi 기반 동적 공역 분할 + 섹터 부하 균형
///
/// 기능:
///   - 동적 Voronoi 공역 분할
///   - 섹터별 부하 모니터링
///   - 핸드오프 프로토콜
///   - LINQ 기반 쿼리
/// </summary>

using System;
using System.Collections.Generic;
using System.Linq;

namespace SDACS.Airspace
{
    public record Vec3(double X, double Y, double Z)
    {
        public double DistanceTo(Vec3 other) =>
            Math.Sqrt(Math.Pow(X - other.X, 2) + Math.Pow(Y - other.Y, 2) + Math.Pow(Z - other.Z, 2));

        public double HorizontalDistanceTo(Vec3 other) =>
            Math.Sqrt(Math.Pow(X - other.X, 2) + Math.Pow(Y - other.Y, 2));
    }

    public record DroneInfo(string DroneId, Vec3 Position, double Battery, string Status);

    public record Sector(
        string SectorId,
        Vec3 Center,
        double Radius,
        double MinAlt,
        double MaxAlt,
        int Capacity,
        List<string> AssignedDrones
    );

    public record HandoffEvent(
        string DroneId,
        string FromSector,
        string ToSector,
        DateTime Timestamp,
        string Reason
    );

    public class AirspacePartition
    {
        private readonly Dictionary<string, Sector> _sectors = new();
        private readonly Dictionary<string, DroneInfo> _drones = new();
        private readonly List<HandoffEvent> _handoffs = new();
        private readonly double _areaSize;

        public AirspacePartition(double areaSize = 1000.0)
        {
            _areaSize = areaSize;
        }

        /// <summary>섹터 추가</summary>
        public void AddSector(string sectorId, Vec3 center, double radius,
            double minAlt = 0, double maxAlt = 120, int capacity = 50)
        {
            _sectors[sectorId] = new Sector(sectorId, center, radius, minAlt, maxAlt,
                capacity, new List<string>());
        }

        /// <summary>N×N 그리드 자동 생성</summary>
        public void GenerateGrid(int n)
        {
            double cellSize = _areaSize / n;
            for (int i = 0; i < n; i++)
            {
                for (int j = 0; j < n; j++)
                {
                    var center = new Vec3(
                        (i + 0.5) * cellSize,
                        (j + 0.5) * cellSize,
                        60.0
                    );
                    AddSector($"S{i}_{j}", center, cellSize / 2.0);
                }
            }
        }

        /// <summary>드론 위치 업데이트 → 자동 섹터 할당</summary>
        public string? UpdateDrone(string droneId, Vec3 position, double battery = 100)
        {
            _drones[droneId] = new DroneInfo(droneId, position, battery, "ACTIVE");

            // 가장 가까운 섹터 찾기
            var nearest = _sectors.Values
                .OrderBy(s => s.Center.HorizontalDistanceTo(position))
                .FirstOrDefault();

            if (nearest == null) return null;

            // 기존 섹터에서 제거
            foreach (var sector in _sectors.Values)
            {
                sector.AssignedDrones.Remove(droneId);
            }

            // 새 섹터에 할당
            var currentSector = FindDroneSector(droneId);
            nearest.AssignedDrones.Add(droneId);

            // 핸드오프 이벤트 기록
            if (currentSector != null && currentSector != nearest.SectorId)
            {
                _handoffs.Add(new HandoffEvent(
                    droneId, currentSector, nearest.SectorId,
                    DateTime.UtcNow, "AUTOMATIC"
                ));
            }

            return nearest.SectorId;
        }

        /// <summary>드론의 현재 섹터 찾기</summary>
        public string? FindDroneSector(string droneId)
        {
            return _sectors.Values
                .FirstOrDefault(s => s.AssignedDrones.Contains(droneId))
                ?.SectorId;
        }

        /// <summary>섹터 부하 (0.0 ~ 1.0)</summary>
        public double SectorLoad(string sectorId)
        {
            if (!_sectors.TryGetValue(sectorId, out var sector)) return 0;
            return (double)sector.AssignedDrones.Count / sector.Capacity;
        }

        /// <summary>과부하 섹터 조회</summary>
        public List<string> OverloadedSectors(double threshold = 0.8) =>
            _sectors.Values
                .Where(s => (double)s.AssignedDrones.Count / s.Capacity > threshold)
                .Select(s => s.SectorId)
                .ToList();

        /// <summary>섹터 간 균형 점수 (0=균형, 1=불균형)</summary>
        public double BalanceScore()
        {
            var loads = _sectors.Values.Select(s => (double)s.AssignedDrones.Count).ToList();
            if (!loads.Any()) return 0;
            double avg = loads.Average();
            if (avg < 1e-6) return 0;
            double variance = loads.Average(l => Math.Pow(l - avg, 2));
            return Math.Min(1.0, Math.Sqrt(variance) / avg);
        }

        /// <summary>통계 요약</summary>
        public Dictionary<string, object> Summary() => new()
        {
            ["sectors"] = _sectors.Count,
            ["drones"] = _drones.Count,
            ["handoffs"] = _handoffs.Count,
            ["balanceScore"] = Math.Round(BalanceScore(), 3),
            ["overloaded"] = OverloadedSectors().Count
        };
    }
}
