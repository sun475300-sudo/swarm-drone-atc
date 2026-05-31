# realtime_scheduler.nim - Real-time task scheduler for SDACS
# Nim implementation of priority-based real-time scheduling

import std/[algorithm, heapqueue, times, tables, strformat]

type
  TaskPriority* = enum
    tpIdle = 0, tpLow = 1, tpNormal = 2, tpHigh = 3, tpCritical = 4

  TaskStatus* = enum
    tsReady, tsRunning, tsBlocked, tsDone, tsError

  Task* = ref object
    id*:           int
    name*:         string
    priority*:     TaskPriority
    period_ms*:    int
    deadline_ms*:  int
    exec_time_ms*: int
    status*:       TaskStatus
    next_run*:     float
    run_count*:    int

  ScheduleEntry* = object
    task_id*:   int
    start_ms*:  float
    end_ms*:    float
    deadline*:  float
    met*:       bool

  RTScheduler* = ref object
    tasks*:        seq[Task]
    schedule*:     seq[ScheduleEntry]
    current_time*: float
    task_table*:   Table[int, Task]
    next_id*:      int
    deadline_misses*: int
    preemptions*:     int

proc newRTScheduler*(): RTScheduler =
  RTScheduler(
    tasks:        @[],
    schedule:     @[],
    current_time: 0.0,
    task_table:   initTable[int, Task](),
    next_id:      1
  )

proc addTask*(sched: RTScheduler; name: string; priority: TaskPriority;
              period_ms, deadline_ms, exec_time_ms: int): int =
  let id = sched.next_id
  inc sched.next_id
  let task = Task(
    id:           id,
    name:         name,
    priority:     priority,
    period_ms:    period_ms,
    deadline_ms:  deadline_ms,
    exec_time_ms: exec_time_ms,
    status:       tsReady,
    next_run:     0.0
  )
  sched.tasks.add(task)
  sched.task_table[id] = task
  id

proc getReadyTasks*(sched: RTScheduler): seq[Task] =
  sched.tasks.filterIt(
    it.status != tsDone and
    it.next_run <= sched.current_time
  )

proc scheduleEDF*(sched: RTScheduler): Task =
  let ready = sched.getReadyTasks()
  if ready.len == 0:
    return nil
  ready.sortedByIt(it.deadline_ms)[0]

proc scheduleRMS*(sched: RTScheduler): Task =
  let ready = sched.getReadyTasks()
  if ready.len == 0:
    return nil
  ready.sortedByIt(it.period_ms)[0]

proc executeTask*(sched: RTScheduler; task: Task) =
  let start = sched.current_time
  task.status = tsRunning
  sched.current_time += float(task.exec_time_ms)
  let deadline = start + float(task.deadline_ms)
  let met = sched.current_time <= deadline
  if not met:
    inc sched.deadline_misses
  sched.schedule.add(ScheduleEntry(
    task_id:  task.id,
    start_ms: start,
    end_ms:   sched.current_time,
    deadline: deadline,
    met:      met
  ))
  task.run_count += 1
  task.next_run = start + float(task.period_ms)
  task.status = tsReady

proc run*(sched: RTScheduler; duration_ms: int; algorithm: string = "EDF") =
  let end_time = float(duration_ms)
  while sched.current_time < end_time:
    let task =
      if algorithm == "EDF": sched.scheduleEDF()
      else: sched.scheduleRMS()
    if task == nil:
      sched.current_time += 1.0
      continue
    sched.executeTask(task)

proc utilizationCheck*(sched: RTScheduler): float =
  var total = 0.0
  for t in sched.tasks:
    if t.period_ms > 0:
      total += float(t.exec_time_ms) / float(t.period_ms)
  total

proc summary*(sched: RTScheduler): string =
  let util = sched.utilizationCheck()
  let entries = sched.schedule.len
  let missed = sched.deadline_misses
  fmt"RTScheduler: tasks={sched.tasks.len}, entries={entries}, util={util:.2f}, misses={missed}"
