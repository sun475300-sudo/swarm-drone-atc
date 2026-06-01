# Realtime Scheduler — Nim for SDACS time-critical task dispatching
# Phase 593

import tables, heapqueue, times, strformat

type
  Priority* = enum
    pLow = 0, pNormal = 1, pHigh = 2, pCritical = 3

  TaskStatus* = enum
    tsQueued, tsRunning, tsCompleted, tsFailed, tsCancelled

  Task* = ref object
    id*        : string
    priority*  : Priority
    deadline*  : float     ## Unix timestamp
    period*    ## periodic interval (0 = one-shot)
    callback*  : proc()
    status*    : TaskStatus
    execCount* : int

  ScheduleEntry = tuple[deadline: float, taskId: string]

  RTScheduler* = ref object
    tasks*     : Table[string, Task]
    queue*     : HeapQueue[ScheduleEntry]
    tick*      : float  ## simulated time
    missCount* : int
    execCount* : int

proc newTask*(id: string, priority: Priority, deadline: float,
              cb: proc(), period: float = 0.0): Task =
  Task(id: id, priority: priority, deadline: deadline,
       callback: cb, status: tsQueued, period: period)

proc newRTScheduler*(): RTScheduler =
  RTScheduler(tasks: initTable[string, Task](),
               queue: initHeapQueue[ScheduleEntry](),
               tick: epochTime(), missCount: 0, execCount: 0)

proc submit*(s: RTScheduler, task: Task) =
  s.tasks[task.id] = task
  s.queue.push((task.deadline, task.id))

proc tick*(s: RTScheduler) =
  s.tick = epochTime()
  while s.queue.len > 0:
    let (dl, tid) = s.queue[0]
    if dl > s.tick: break
    discard s.queue.pop()

    if tid notin s.tasks: continue
    let task = s.tasks[tid]
    if task.status == tsCancelled: continue

    if dl < s.tick - 0.001:
      inc s.missCount
      task.status = tsFailed
      continue

    task.status = tsRunning
    try:
      task.callback()
      inc task.execCount
      inc s.execCount
      task.status = tsCompleted

      if task.period > 0.0:
        let nextDl = dl + task.period
        task.status = tsQueued
        task.deadline = nextDl
        s.queue.push((nextDl, task.id))
    except:
      task.status = tsFailed
      inc s.missCount

proc cancel*(s: RTScheduler, taskId: string) =
  if taskId in s.tasks:
    s.tasks[taskId].status = tsCancelled

proc stats*(s: RTScheduler): string =
  fmt"RTScheduler: {s.execCount} executed, {s.missCount} missed, {s.tasks.len} registered"

proc runFor*(s: RTScheduler, seconds: float) =
  let endTime = epochTime() + seconds
  while epochTime() < endTime:
    s.tick()

# Example usage
when isMainModule:
  let sched = newRTScheduler()

  let t1 = newTask("heartbeat", pHigh, epochTime() + 0.1,
    proc() = echo "Heartbeat sent", period = 1.0)
  let t2 = newTask("telemetry", pNormal, epochTime() + 0.05,
    proc() = echo "Telemetry broadcast")
  let t3 = newTask("conflict-check", pCritical, epochTime() + 0.02,
    proc() = echo "Conflict check passed")

  sched.submit(t1)
  sched.submit(t2)
  sched.submit(t3)

  sched.runFor(0.5)
  echo sched.stats()
