# Phase 593: Realtime Scheduler — 드론 실시간 스케줄러 (Nim)
# Fixed-priority preemptive real-time task scheduler for drone operations.

import std/[heapqueue, times, math, strformat, random]

const PHASE* = 593

# ── Task priority levels ───────────────────────────────────────────

type
  TaskPriority* = enum
    Idle = 0, Low = 1, Normal = 2, High = 3, Critical = 4

  TaskState* = enum
    Ready, Running, Blocked, Completed

  RTTask* = object
    id*:        int
    name*:      string
    priority*:  TaskPriority
    period_ms*: float64    # periodic task interval
    deadline*:  float64    # absolute deadline (ms from start)
    exec_time*: float64    # worst-case execution time (ms)
    state*:     TaskState
    jitter_ms*: float64    # measured scheduling jitter
    releases*:  int        # number of times scheduled
    misses*:    int        # deadline misses

  RTTaskQueue* = HeapQueue[(int, int, RTTask)]  # (neg_priority, seq, task)

# ── RTScheduler ───────────────────────────────────────────────────

type RTScheduler* = ref object
  tasks*:       seq[RTTask]
  queue*:       RTTaskQueue
  clock_ms*:    float64
  tick_ms*:     float64
  jitter_hist*: seq[float64]
  rng*:         Rand
  name*:        string

proc newRTScheduler*(tick_ms: float64, seed: int64): RTScheduler =
  RTScheduler(
    tasks:       @[],
    queue:       initHeapQueue[(int, int, RTTask)](),
    clock_ms:    0.0,
    tick_ms:     tick_ms,
    jitter_hist: @[],
    rng:         initRand(seed),
    name:        "RTScheduler"
  )

proc addTask*(sched: RTScheduler, task: RTTask) =
  sched.tasks.add(task)

proc releaseTask*(sched: RTScheduler, task: var RTTask) =
  task.state    = Ready
  task.releases += 1
  task.deadline  = sched.clock_ms + task.period_ms
  let seq_id = task.releases
  sched.queue.push((-ord(task.priority), seq_id, task))

proc executeTask*(sched: RTScheduler, task: var RTTask) =
  task.state = Running
  let noise = sched.rng.rand(0.5) - 0.25
  let actual_exec = task.exec_time + noise
  sched.clock_ms += actual_exec
  let jitter = abs(actual_exec - task.exec_time)
  task.jitter_ms = jitter
  sched.jitter_hist.add(jitter)
  if sched.clock_ms > task.deadline:
    task.misses += 1
  task.state = Completed

proc tick*(sched: RTScheduler) =
  sched.clock_ms += sched.tick_ms
  # Release periodic tasks
  for i in 0 ..< sched.tasks.len:
    let t = sched.tasks[i]
    if t.period_ms > 0 and
       sched.clock_ms.int mod t.period_ms.int == 0:
      var mt = sched.tasks[i]
      sched.releaseTask(mt)
      sched.tasks[i] = mt

  # Run highest-priority ready task
  if sched.queue.len > 0:
    let (_, _, task) = sched.queue.pop()
    var mt = task
    sched.executeTask(mt)

proc run*(sched: RTScheduler, n_ticks: int) =
  for _ in 0 ..< n_ticks:
    sched.tick()

proc utilization*(sched: RTScheduler): float64 =
  var u = 0.0
  for t in sched.tasks:
    if t.period_ms > 0:
      u += t.exec_time / t.period_ms
  u

proc avgJitter*(sched: RTScheduler): float64 =
  if sched.jitter_hist.len == 0: return 0.0
  sched.jitter_hist.foldl(a + b, 0.0) / float64(sched.jitter_hist.len)

proc summary*(sched: RTScheduler): string =
  let misses = sched.tasks.foldl(a + b.misses, 0)
  fmt"Phase {PHASE}: {sched.name} ticks={sched.clock_ms.int} tasks={sched.tasks.len} " &
  fmt"util={sched.utilization():.2f} misses={misses} avgJitter={sched.avgJitter():.3f}ms"

# ── Entry point ────────────────────────────────────────────────────

when isMainModule:
  echo fmt"Phase {PHASE}: Realtime Scheduler — 드론 실시간 태스크 스케줄러"
  let sched = newRTScheduler(1.0, 42)

  sched.addTask(RTTask(id: 0, name: "flight_ctrl",   priority: Critical, period_ms: 10, exec_time: 2.0, deadline: 10.0))
  sched.addTask(RTTask(id: 1, name: "nav_update",    priority: High,     period_ms: 20, exec_time: 3.0, deadline: 20.0))
  sched.addTask(RTTask(id: 2, name: "telemetry_tx",  priority: Normal,   period_ms: 50, exec_time: 5.0, deadline: 50.0))
  sched.addTask(RTTask(id: 3, name: "battery_check", priority: Low,      period_ms: 100, exec_time: 1.0, deadline: 100.0))

  sched.run(200)
  echo sched.summary()
