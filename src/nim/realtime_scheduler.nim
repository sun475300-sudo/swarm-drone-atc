# Realtime Scheduler — SDACS Phase 593
# Priority-based realtime task scheduler for drone control

import asyncdispatch, heapqueue, times, strformat

type
  Priority* = enum
    LOW = 0, MEDIUM = 1, HIGH = 2, CRITICAL = 3

  Task* = ref object
    id*       : string
    priority* : Priority
    interval* : int  ## milliseconds
    handler*  : proc() {.async.}
    lastRun*  : float
    enabled*  : bool

  RTScheduler* = ref object
    tasks     : seq[Task]
    running   : bool
    tickMs    : int

proc newTask*(id: string, prio: Priority, interval: int, handler: proc() {.async.}): Task =
  Task(id: id, priority: prio, interval: interval,
       handler: handler, lastRun: 0.0, enabled: true)

proc newRTScheduler*(tickMs: int = 10): RTScheduler =
  RTScheduler(tasks: @[], running: false, tickMs: tickMs)

proc add*(s: RTScheduler, task: Task) =
  s.tasks.add(task)

proc remove*(s: RTScheduler, id: string) =
  s.tasks.keepIf(proc(t: Task): bool = t.id != id)

proc start*(s: RTScheduler) {.async.} =
  s.running = true
  while s.running:
    let now = epochTime() * 1000
    for task in s.tasks:
      if task.enabled and (now - task.lastRun) >= task.interval.float:
        task.lastRun = now
        await task.handler()
    await sleepAsync(s.tickMs)

proc stop*(s: RTScheduler) =
  s.running = false

proc taskCount*(s: RTScheduler): int = s.tasks.len
# end
# end
# end
