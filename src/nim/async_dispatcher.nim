# Phase 649: Async Dispatcher — 비동기 드론 임무 디스패처 (Nim)
# Coroutine-based async task dispatcher for swarm drone missions.

import std/[asyncdispatch, asyncfutures, tables, deques, random, strformat, times]

const PHASE* = 649
const MAX_WORKERS* = 8

type
  TaskKind* = enum
    Navigate, Survey, Deliver, Hover, Return

  MissionTask* = object
    id*: int
    drone_id*: int
    kind*: TaskKind
    priority*: int
    payload*: string

  TaskResult* = object
    task_id*: int
    success*: bool
    elapsed_ms*: float
    msg*: string

  AsyncDispatcher* = ref object
    queue*: Deque[MissionTask]
    results*: seq[TaskResult]
    worker_count*: int
    dispatched*: int
    rng*: Rand

# ── Task construction helpers ──────────────────────────────────────

proc newTask*(id, drone_id: int, kind: TaskKind, priority: int): MissionTask =
  MissionTask(id: id, drone_id: drone_id, kind: kind, priority: priority,
              payload: fmt"task-{id}-drone-{drone_id}")

proc newDispatcher*(n_workers: int, seed: int64): AsyncDispatcher =
  result = AsyncDispatcher(
    queue: initDeque[MissionTask](),
    results: @[],
    worker_count: min(n_workers, MAX_WORKERS),
    dispatched: 0,
    rng: initRand(seed)
  )

# ── Queue operations ───────────────────────────────────────────────

proc enqueue*(d: AsyncDispatcher, task: MissionTask) =
  d.queue.addLast(task)

proc bulkEnqueue*(d: AsyncDispatcher, tasks: seq[MissionTask]) =
  for t in tasks:
    d.enqueue(t)

# ── Async task execution ───────────────────────────────────────────

proc executeTask(d: AsyncDispatcher, task: MissionTask): Future[TaskResult] {.async.} =
  let t0 = epochTime()
  # Simulate async work with a tiny sleep
  await sleepAsync(1)
  let elapsed = (epochTime() - t0) * 1000.0
  let success = task.priority > 0
  result = TaskResult(
    task_id: task.id,
    success: success,
    elapsed_ms: elapsed,
    msg: fmt"[Phase {PHASE}] drone-{task.drone_id} completed {task.kind}"
  )

proc runWorker(d: AsyncDispatcher): Future[void] {.async.} =
  while d.queue.len > 0:
    let task = d.queue.popFirst()
    d.dispatched += 1
    let r = await d.executeTask(task)
    d.results.add(r)

# ── Dispatcher run ─────────────────────────────────────────────────

proc run*(d: AsyncDispatcher): Future[void] {.async.} =
  ## Spawn up to worker_count concurrent workers.
  var futures: seq[Future[void]] = @[]
  for _ in 0 ..< d.worker_count:
    futures.add(d.runWorker())
  for f in futures:
    await f

proc runSync*(d: AsyncDispatcher) =
  waitFor d.run()

# ── Statistics ─────────────────────────────────────────────────────

proc successRate*(d: AsyncDispatcher): float =
  if d.results.len == 0: return 0.0
  let ok = d.results.filterIt(it.success).len
  float(ok) / float(d.results.len)

proc summary*(d: AsyncDispatcher): string =
  let sr = d.successRate()
  fmt"Phase {PHASE}: dispatched={d.dispatched} results={d.results.len} success_rate={sr:.2f}"

# ── Entry point ────────────────────────────────────────────────────

when isMainModule:
  echo fmt"Phase {PHASE}: Async Dispatcher — 비동기 드론 임무 디스패처"
  let disp = newDispatcher(4, 42)
  var tasks: seq[MissionTask] = @[]
  for i in 0 ..< 20:
    tasks.add(newTask(i, i mod 5, Navigate, i mod 3 + 1))
  disp.bulkEnqueue(tasks)
  disp.runSync()
  echo disp.summary()
