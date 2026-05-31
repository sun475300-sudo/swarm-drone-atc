# Phase 593 — Nim real-time scheduler with RingBuffer
# SDACS real-time event queue and scheduling for drone telemetry

import std/[times, math, strformat]

# ---- RingBuffer ----

type
  RingBuffer*[T] = object
    ## Lock-free single-producer single-consumer ring buffer
    data*    : seq[T]
    capacity : int
    head     : int   # write index
    tail     : int   # read index
    count    : int

proc initRingBuffer*[T](cap: int): RingBuffer[T] =
  ## Initialise a RingBuffer with the given capacity
  assert cap > 0, "RingBuffer capacity must be > 0"
  result.data     = newSeq[T](cap)
  result.capacity = cap
  result.head     = 0
  result.tail     = 0
  result.count    = 0

proc isFull*[T](rb: RingBuffer[T]): bool {.inline.} =
  rb.count >= rb.capacity

proc isEmpty*[T](rb: RingBuffer[T]): bool {.inline.} =
  rb.count == 0

proc len*[T](rb: RingBuffer[T]): int {.inline.} =
  rb.count

proc push*[T](rb: var RingBuffer[T], item: T): bool =
  ## Enqueue an item. Returns false if the buffer is full.
  if rb.isFull: return false
  rb.data[rb.head] = item
  rb.head = (rb.head + 1) mod rb.capacity
  inc rb.count
  true

proc pop*[T](rb: var RingBuffer[T]): (bool, T) =
  ## Dequeue an item. Returns (false, default) if empty.
  var item: T
  if rb.isEmpty: return (false, item)
  item = rb.data[rb.tail]
  rb.tail = (rb.tail + 1) mod rb.capacity
  dec rb.count
  (true, item)

proc peek*[T](rb: RingBuffer[T]): (bool, T) =
  ## Peek at the next item without removing it.
  var item: T
  if rb.isEmpty: return (false, item)
  (true, rb.data[rb.tail])

# ---- Domain Types ----

type
  DroneEventKind* = enum
    evTelemetry = "telemetry"
    evCommand   = "command"
    evConflict  = "conflict"
    evHeartbeat = "heartbeat"

  DroneEvent* = object
    kind*       : DroneEventKind
    droneId*    : int
    timestampMs*: int64
    payload*    : string   # JSON-like string payload

  SchedulerPriority* = enum
    PriorityLow    = 0
    PriorityNormal = 1
    PriorityHigh   = 2

  ScheduledTask* = object
    id*         : int
    name*       : string
    intervalMs* : int
    priority*   : SchedulerPriority
    lastRunMs*  : int64
    runCount*   : int

# ---- Real-Time Scheduler ----

type
  RTScheduler* = object
    tasks*     : seq[ScheduledTask]
    eventQueue*: RingBuffer[DroneEvent]
    running*   : bool
    tickCount* : int64
    startMs*   : int64

proc initRTScheduler*(queueCap: int = 256): RTScheduler =
  result.tasks      = @[]
  result.eventQueue = initRingBuffer[DroneEvent](queueCap)
  result.running    = false
  result.tickCount  = 0
  result.startMs    = 0

proc addTask*(sched: var RTScheduler, name: string, intervalMs: int,
              priority: SchedulerPriority = PriorityNormal): int =
  ## Register a periodic task and return its id
  let id = sched.tasks.len
  sched.tasks.add ScheduledTask(
    id: id, name: name, intervalMs: intervalMs,
    priority: priority, lastRunMs: 0, runCount: 0
  )
  id

proc enqueueEvent*(sched: var RTScheduler, evt: DroneEvent): bool =
  ## Push a drone event onto the ring buffer
  sched.eventQueue.push(evt)

proc processEvents*(sched: var RTScheduler, maxProcess: int = 16) =
  ## Drain up to maxProcess events from the ring buffer
  var processed = 0
  while processed < maxProcess:
    let (ok, evt) = sched.eventQueue.pop()
    if not ok: break
    echo fmt"[sched] processed {evt.kind} from drone {evt.droneId} ts={evt.timestampMs}"
    inc processed

proc tick*(sched: var RTScheduler, nowMs: int64) =
  ## Execute all tasks whose interval has elapsed
  inc sched.tickCount
  for task in sched.tasks.mitems:
    if nowMs - task.lastRunMs >= task.intervalMs:
      echo fmt"[tick {sched.tickCount}] task '{task.name}' (pri={task.priority}) run #{task.runCount + 1}"
      task.lastRunMs = nowMs
      inc task.runCount

# ---- Smoke Test ----

var sched = initRTScheduler(64)
discard sched.addTask("telemetry_ingest", 100, PriorityHigh)
discard sched.addTask("conflict_check",   500, PriorityNormal)
discard sched.addTask("heartbeat_sweep", 1000, PriorityLow)

let ev1 = DroneEvent(kind: evTelemetry, droneId: 1, timestampMs: 1000, payload: "{alt:80}")
let ev2 = DroneEvent(kind: evHeartbeat, droneId: 2, timestampMs: 1001, payload: "{seq:1}")

discard sched.enqueueEvent(ev1)
discard sched.enqueueEvent(ev2)

for t in [0'i64, 100, 200, 500, 1000]:
  sched.tick(t)

sched.processEvents(10)

echo fmt"RingBuffer remaining: {sched.eventQueue.len}"
echo fmt"Tick count: {sched.tickCount}"
