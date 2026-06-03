# Phase 583: Real-Time Scheduler — Nim
# SDACS hard real-time task scheduler with deadline monitoring

import std/[times, monotimes, heapqueue, tables, strformat, options]

type
  Priority* = enum
    pCritical = 0
    pHigh     = 1
    pNormal   = 2
    pLow      = 3

  TaskState* = enum
    tsReady, tsRunning, tsBlocked, tsCompleted, tsMissed

  Task* = object
    id*           : string
    priority*     : Priority
    period_ns*    : int64       ## periodic interval in nanoseconds
    deadline_ns*  : int64       ## deadline relative to period start
    wcet_ns*      : int64       ## worst-case execution time estimate
    next_release* : int64       ## absolute monotime of next release
    state*        : TaskState
    miss_count*   : int
    exec_count*   : int

  RTScheduler* = object
    tasks*        : Table[string, Task]
    ready_queue*  : HeapQueue[(int64, string)]  ## (priority_key, task_id)
    tick_ns*      : int64
    deadline_misses* : int
    total_exec*   : int

  SchedulerStats* = object
    total_tasks*     : int
    total_executions*: int
    deadline_misses* : int
    utilization*     : float
    uptime_s*        : float

proc newRTScheduler*(tick_us: int = 1000): RTScheduler =
  result = RTScheduler(
    tasks:           initTable[string, Task](),
    ready_queue:     initHeapQueue[(int64, string)](),
    tick_ns:         tick_us.int64 * 1000,
    deadline_misses: 0,
    total_exec:      0,
  )

proc addTask*(sched: var RTScheduler, id: string, priority: Priority,
              period_ms: int, deadline_ms: int, wcet_us: int) =
  let now = getMonoTime().ticks
  let task = Task(
    id:           id,
    priority:     priority,
    period_ns:    period_ms.int64 * 1_000_000,
    deadline_ns:  deadline_ms.int64 * 1_000_000,
    wcet_ns:      wcet_us.int64 * 1_000,
    next_release: now,
    state:        tsReady,
    miss_count:   0,
    exec_count:   0,
  )
  sched.tasks[id] = task

proc removeTask*(sched: var RTScheduler, id: string) =
  sched.tasks.del(id)

proc releaseReady*(sched: var RTScheduler) =
  let now = getMonoTime().ticks
  for id, task in sched.tasks.mpairs:
    if task.state == tsReady and task.next_release <= now:
      # Priority key: lower value = higher priority; use -(deadline) for EDF
      let deadline_abs = task.next_release + task.deadline_ns
      let key = deadline_abs  # Earliest Deadline First
      sched.ready_queue.push((key, id))

proc checkDeadlines*(sched: var RTScheduler) =
  let now = getMonoTime().ticks
  for id, task in sched.tasks.mpairs:
    if task.state == tsRunning:
      let deadline_abs = task.next_release + task.deadline_ns
      if now > deadline_abs:
        sched.tasks[id].state = tsMissed
        sched.tasks[id].miss_count += 1
        sched.deadline_misses += 1

proc nextTask*(sched: var RTScheduler): Option[string] =
  sched.releaseReady()
  sched.checkDeadlines()
  if sched.ready_queue.len == 0:
    return none(string)
  let (_, id) = sched.ready_queue.pop()
  if id in sched.tasks:
    sched.tasks[id].state = tsRunning
    return some(id)
  none(string)

proc completeTask*(sched: var RTScheduler, id: string) =
  if id notin sched.tasks: return
  sched.tasks[id].state = tsReady
  sched.tasks[id].next_release += sched.tasks[id].period_ns
  sched.tasks[id].exec_count += 1
  sched.total_exec += 1

proc utilization*(sched: RTScheduler): float =
  var total = 0.0
  for _, task in sched.tasks:
    if task.period_ns > 0:
      total += task.wcet_ns.float / task.period_ns.float
  total

proc stats*(sched: RTScheduler): SchedulerStats =
  SchedulerStats(
    total_tasks:      sched.tasks.len,
    total_executions: sched.total_exec,
    deadline_misses:  sched.deadline_misses,
    utilization:      sched.utilization(),
    uptime_s:         0.0,  # populated by caller
  )

proc schedulable*(sched: RTScheduler): bool =
  ## Rate-monotonic schedulability bound (Liu & Layland)
  let n = sched.tasks.len.float
  let bound = n * (2.0.pow(1.0/n) - 1.0)
  sched.utilization() <= bound

proc `$`*(task: Task): string =
  fmt"Task({task.id} prio={task.priority} exec={task.exec_count} miss={task.miss_count})"

proc `$`*(stats: SchedulerStats): string =
  fmt"Stats(tasks={stats.total_tasks} exec={stats.total_executions} " &
  fmt"miss={stats.deadline_misses} util={stats.utilization:.2f})"

when isMainModule:
  var sched = newRTScheduler(1000)
  sched.addTask("control_loop",  pCritical, 10,  10,  500)
  sched.addTask("telemetry_tx",  pHigh,     50,  45,  1000)
  sched.addTask("battery_check", pNormal,   1000, 900, 200)
  sched.addTask("log_writer",    pLow,      5000, 4500, 5000)

  echo fmt"Scheduler created with {sched.tasks.len} tasks"
  echo fmt"Schedulable: {sched.schedulable()}"
  echo fmt"Utilization: {sched.utilization():.3f}"

  let next = sched.nextTask()
  if next.isSome:
    echo fmt"Next task: {next.get()}"
    sched.completeTask(next.get())

  echo $sched.stats()
