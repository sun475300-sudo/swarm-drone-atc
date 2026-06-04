/**
 * Phase 296: C# Mission Orchestrator — 미션 오케스트레이터
 * LINQ 기반 작업 스케줄링, DAG 의존성 관리, 이벤트 기반 진행 추적.
 */

using System;
using System.Collections.Generic;
using System.Linq;

namespace SDACS.Mission
{
    public enum MissionType { Surveillance, Delivery, SearchRescue, Mapping, Inspection, Patrol }
    public enum TaskState { Waiting, Ready, Running, Completed, Failed, Cancelled }

    public class MissionTask
    {
        public string TaskId { get; set; }
        public string MissionId { get; set; }
        public string TaskType { get; set; }
        public double[] Position { get; set; }
        public double DurationSec { get; set; } = 60.0;
        public TaskState State { get; set; } = TaskState.Waiting;
        public string AssignedDrone { get; set; }
        public List<string> Dependencies { get; set; } = new List<string>();
        public double Progress { get; set; } = 0.0;
        public int Priority { get; set; } = 5;
    }

    public class Mission
    {
        public string MissionId { get; set; }
        public MissionType Type { get; set; }
        public List<MissionTask> Tasks { get; set; } = new List<MissionTask>();
        public string Status { get; set; } = "pending";
        public int Priority { get; set; } = 5;
    }

    public class MissionOrchestrator
    {
        private readonly Dictionary<string, Mission> _missions = new Dictionary<string, Mission>();
        private readonly Dictionary<string, string> _droneAssignments = new Dictionary<string, string>();
        private readonly List<Dictionary<string, object>> _history = new List<Dictionary<string, object>>();

        public Mission CreateMission(string missionId, MissionType type, int priority = 5)
        {
            var mission = new Mission { MissionId = missionId, Type = type, Priority = priority };
            _missions[missionId] = mission;
            return mission;
        }

        public bool AddTask(string missionId, MissionTask task)
        {
            if (!_missions.TryGetValue(missionId, out var mission)) return false;
            task.MissionId = missionId;
            mission.Tasks.Add(task);
            return true;
        }

        public List<MissionTask> StartMission(string missionId)
        {
            if (!_missions.TryGetValue(missionId, out var mission)) return new List<MissionTask>();
            mission.Status = "active";
            return GetReadyTasks(mission);
        }

        private List<MissionTask> GetReadyTasks(Mission mission)
        {
            var completed = mission.Tasks
                .Where(t => t.State == TaskState.Completed)
                .Select(t => t.TaskId)
                .ToHashSet();

            return mission.Tasks
                .Where(t => t.State == TaskState.Waiting && t.Dependencies.All(d => completed.Contains(d)))
                .Select(t => { t.State = TaskState.Ready; return t; })
                .ToList();
        }

        public bool AssignDrone(string taskId, string droneId)
        {
            foreach (var mission in _missions.Values)
            {
                var task = mission.Tasks.FirstOrDefault(t => t.TaskId == taskId);
                if (task != null)
                {
                    task.AssignedDrone = droneId;
                    task.State = TaskState.Running;
                    _droneAssignments[droneId] = taskId;
                    return true;
                }
            }
            return false;
        }

        public List<MissionTask> CompleteTask(string taskId)
        {
            foreach (var mission in _missions.Values)
            {
                var task = mission.Tasks.FirstOrDefault(t => t.TaskId == taskId);
                if (task != null)
                {
                    task.State = TaskState.Completed;
                    task.Progress = 1.0;
                    if (task.AssignedDrone != null) _droneAssignments.Remove(task.AssignedDrone);
                    _history.Add(new Dictionary<string, object> {
                        {"event", "task_complete"}, {"task", taskId}, {"mission", mission.MissionId}
                    });

                    if (mission.Tasks.All(t => t.State == TaskState.Completed))
                    {
                        mission.Status = "completed";
                    }
                    return GetReadyTasks(mission);
                }
            }
            return new List<MissionTask>();
        }

        public double GetMissionProgress(string missionId)
        {
            if (!_missions.TryGetValue(missionId, out var mission) || !mission.Tasks.Any()) return 0.0;
            return (double)mission.Tasks.Count(t => t.State == TaskState.Completed) / mission.Tasks.Count;
        }

        public Dictionary<string, object> Summary()
        {
            var statuses = _missions.Values.GroupBy(m => m.Status).ToDictionary(g => g.Key, g => g.Count());
            var totalTasks = _missions.Values.Sum(m => m.Tasks.Count);
            var completedTasks = _missions.Values.Sum(m => m.Tasks.Count(t => t.State == TaskState.Completed));

            return new Dictionary<string, object>
            {
                {"totalMissions", _missions.Count},
                {"missionStatuses", statuses},
                {"totalTasks", totalTasks},
                {"completedTasks", completedTasks},
                {"activeDroneAssignments", _droneAssignments.Count},
            };
        }
    }
}
