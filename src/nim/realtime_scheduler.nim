# P593: RealtimeScheduler - Nim real-time task scheduling
# Phase 593: RTScheduler for periodic drone control tasks

import times
import tables
import heapqueue
import strformat
import math

type
  Priority = enum
    Critical = 0
    High     = 1
    Normal   = 2
    Low      = 3

  TaskState = enum
    Pending, Running, Completed, Overrun

  RTTask = ref object
    id:          string
    period_ms:   float
    deadline_ms: float
    priority:    Priority
    callback:    proc()
    last_run:    float
    next_run:    float
    run_count:   int
    overruns:    int
    state:       TaskState

  RTScheduler* = ref object
    tasks:        Table[string, RTTask]
    tick_ms:      float
    current_time: float
    total_ticks:  int
    missed_dl:    int
    enabled:      bool

proc newRTScheduler*(tick_ms: float = 1.0): RTScheduler =
  RTScheduler(
    tasks:        initTable[string, RTTask](),
    tick_ms:      tick_ms,
    current_time: 0.0,
    total_ticks:  0,
    missed_dl:    0,
    enabled:      true
  )

proc addTask*(sched: RTScheduler, id: string, period_ms: float,
              priority: Priority = Normal, callback: proc() = proc() = discard) =
  sched.tasks[id] = RTTask(
    id:          id,
    period_ms:   period_ms,
    deadline_ms: period_ms,  # implicit deadline = period
    priority:    priority,
    callback:    callback,
    last_run:    0.0,
    next_run:    period_ms,
    run_count:   0,
    overruns:    0,
    state:       Pending
  )

proc removeTask*(sched: RTScheduler, id: string) =
  sched.tasks.del(id)

proc tick*(sched: RTScheduler) =
  if not sched.enabled: return
  sched.current_time += sched.tick_ms
  sched.total_ticks  += 1

  # Find all tasks due to run (sorted by priority)
  var due: seq[RTTask] = @[]
  for _, task in sched.tasks:
    if sched.current_time >= task.next_run:
      due.add(task)

  # Sort by priority (lower enum = higher priority)
  due.sort(proc(a, b: RTTask): int = cmp(a.priority.ord, b.priority.ord))

  for task in due:
    let t_start = sched.current_time
    task.state = Running
    try:
      task.callback()
    except:
      discard
    task.state = Completed
    task.run_count += 1
    task.last_run   = sched.current_time
    task.next_run   = sched.current_time + task.period_ms

    let elapsed = sched.current_time - t_start
    if elapsed > task.deadline_ms:
      task.overruns += 1
      sched.missed_dl += 1

proc runFor*(sched: RTScheduler, duration_ms: float) =
  let end_time = sched.current_time + duration_ms
  while sched.current_time < end_time:
    sched.tick()

proc stats*(sched: RTScheduler): Table[string, int] =
  result = initTable[string, int]()
  result["total_ticks"]  = sched.total_ticks
  result["missed_dl"]    = sched.missed_dl
  result["task_count"]   = sched.tasks.len
  for id, task in sched.tasks:
    result[&"task_{id}_runs"] = task.run_count
    result[&"task_{id}_overruns"] = task.overruns

proc utilization*(sched: RTScheduler): float =
  ## Compute CPU utilization using Liu-Layland bound: sum(Ci/Ti)
  var util = 0.0
  for _, task in sched.tasks:
    util += sched.tick_ms / task.period_ms
  util
