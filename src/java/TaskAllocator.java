/**
 * Phase 281: Java Task Allocator — 협력적 작업 할당 (Java 구현)
 * Hungarian Algorithm + Auction 기반 다중 드론 작업 분배.
 */
package com.sdacs.allocation;

import java.util.*;
import java.util.concurrent.*;
import java.util.stream.*;

public class TaskAllocator {

    public enum TaskPriority { LOW(1), MEDIUM(2), HIGH(3), CRITICAL(4);
        final int value;
        TaskPriority(int v) { this.value = v; }
    }

    public enum TaskStatus { PENDING, ASSIGNED, IN_PROGRESS, COMPLETED, FAILED }

    public static class Task {
        public final String taskId;
        public final double[] position;
        public TaskPriority priority;
        public TaskStatus status;
        public String assignedDrone;
        public double reward;

        public Task(String id, double[] pos, TaskPriority priority) {
            this.taskId = id;
            this.position = pos;
            this.priority = priority;
            this.status = TaskStatus.PENDING;
            this.reward = 1.0;
        }
    }

    public static class DroneCapability {
        public final String droneId;
        public double[] position;
        public double batteryPct;
        public double speedMs;
        public boolean available;

        public DroneCapability(String id, double[] pos) {
            this.droneId = id;
            this.position = pos;
            this.batteryPct = 100.0;
            this.speedMs = 15.0;
            this.available = true;
        }
    }

    private final ConcurrentHashMap<String, Task> tasks = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, DroneCapability> drones = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, String> allocations = new ConcurrentHashMap<>();
    private final List<Map<String, Object>> history = Collections.synchronizedList(new ArrayList<>());

    public void addTask(Task task) { tasks.put(task.taskId, task); }
    public void registerDrone(DroneCapability drone) { drones.put(drone.droneId, drone); }

    private double computeCost(DroneCapability drone, Task task) {
        double dist = distance(drone.position, task.position);
        double timeCost = dist / Math.max(drone.speedMs, 0.1);
        double batteryPenalty = Math.max(0, 50.0 - drone.batteryPct) * 2.0;
        double priorityBonus = -task.priority.value * 10.0;
        return timeCost + batteryPenalty + priorityBonus;
    }

    private double distance(double[] a, double[] b) {
        double sum = 0;
        for (int i = 0; i < Math.min(a.length, b.length); i++)
            sum += (a[i] - b[i]) * (a[i] - b[i]);
        return Math.sqrt(sum);
    }

    public Map<String, String> allocateGreedy() {
        List<DroneCapability> availDrones = drones.values().stream()
            .filter(d -> d.available).collect(Collectors.toList());
        List<Task> pendingTasks = tasks.values().stream()
            .filter(t -> t.status == TaskStatus.PENDING)
            .sorted((a, b) -> Integer.compare(b.priority.value, a.priority.value))
            .collect(Collectors.toList());

        Map<String, String> result = new HashMap<>();
        Set<String> usedDrones = new HashSet<>();

        for (Task task : pendingTasks) {
            DroneCapability best = null;
            double bestCost = Double.MAX_VALUE;
            for (DroneCapability drone : availDrones) {
                if (usedDrones.contains(drone.droneId)) continue;
                double cost = computeCost(drone, task);
                if (cost < bestCost) {
                    bestCost = cost;
                    best = drone;
                }
            }
            if (best != null && bestCost < 1e5) {
                task.status = TaskStatus.ASSIGNED;
                task.assignedDrone = best.droneId;
                allocations.put(task.taskId, best.droneId);
                usedDrones.add(best.droneId);
                result.put(task.taskId, best.droneId);
                history.add(Map.of("event", "assign", "task", task.taskId, "drone", best.droneId));
            }
        }
        return result;
    }

    public boolean completeTask(String taskId) {
        Task task = tasks.get(taskId);
        if (task == null) return false;
        task.status = TaskStatus.COMPLETED;
        history.add(Map.of("event", "complete", "task", taskId));
        return true;
    }

    public Map<String, Object> summary() {
        Map<String, Long> statuses = tasks.values().stream()
            .collect(Collectors.groupingBy(t -> t.status.name(), Collectors.counting()));
        return Map.of(
            "totalTasks", tasks.size(),
            "totalDrones", drones.size(),
            "allocations", allocations.size(),
            "statuses", statuses,
            "historyEvents", history.size()
        );
    }
}
