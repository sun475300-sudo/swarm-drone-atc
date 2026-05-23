# Phase 659: Async Dispatcher — Nim Asynchronous Event Dispatcher
# 비동기 이벤트 디스패처: 멀티드론 텔레메트리 이벤트 라우팅

import std/[asyncdispatch, tables, times, strformat, sequtils, random]

type
  EventPriority* = enum
    epCritical = 0
    epHigh = 1
    epNormal = 2
    epLow = 3

  DroneEvent* = object
    droneId*: string
    eventType*: string
    priority*: EventPriority
    timestamp*: float64
    data*: Table[string, string]

  EventHandler* = proc(event: DroneEvent): Future[void]

  DispatcherStats* = object
    totalDispatched*: int
    totalDropped*: int
    avgLatencyMs*: float64
    queueDepth*: int

  AsyncDispatcher* = ref object
    handlers: Table[string, seq[EventHandler]]
    queue: seq[DroneEvent]
    maxQueueSize: int
    stats: DispatcherStats
    running: bool

proc newDispatcher*(maxQueue: int = 1000): AsyncDispatcher =
  result = AsyncDispatcher(
    handlers: initTable[string, seq[EventHandler]](),
    queue: @[],
    maxQueueSize: maxQueue,
    stats: DispatcherStats(),
    running: false
  )

proc subscribe*(d: AsyncDispatcher, eventType: string, handler: EventHandler) =
  if eventType notin d.handlers:
    d.handlers[eventType] = @[]
  d.handlers[eventType].add(handler)

proc publish*(d: AsyncDispatcher, event: DroneEvent) =
  if d.queue.len >= d.maxQueueSize:
    # Drop lowest priority events
    d.stats.totalDropped += 1
    if event.priority <= epHigh:
      # High priority: find and replace a low priority event
      var replaced = false
      for i in countdown(d.queue.high, 0):
        if d.queue[i].priority > event.priority:
          d.queue[i] = event
          replaced = true
          break
      if not replaced:
        d.stats.totalDropped += 1
  else:
    d.queue.add(event)
    d.stats.queueDepth = d.queue.len

proc dispatch*(d: AsyncDispatcher): Future[int] {.async.} =
  ## Process all events in queue, return count processed
  var processed = 0

  # Sort by priority (critical first)
  d.queue.sort(proc(a, b: DroneEvent): int =
    ord(a.priority) - ord(b.priority)
  )

  for event in d.queue:
    if event.eventType in d.handlers:
      for handler in d.handlers[event.eventType]:
        await handler(event)
    d.stats.totalDispatched += 1
    processed += 1

  d.queue.setLen(0)
  d.stats.queueDepth = 0
  return processed

proc getStats*(d: AsyncDispatcher): DispatcherStats =
  d.stats

# ── Simulation ───────────────────────────────────────

proc simulateDispatcher*() {.async.} =
  let dispatcher = newDispatcher(500)
  var rng = initRand(42)

  # Register handlers
  dispatcher.subscribe("telemetry", proc(e: DroneEvent): Future[void] {.async.} =
    discard # Process telemetry
  )
  dispatcher.subscribe("alert", proc(e: DroneEvent): Future[void] {.async.} =
    discard # Process alert
  )
  dispatcher.subscribe("advisory", proc(e: DroneEvent): Future[void] {.async.} =
    discard # Process advisory
  )

  # Generate events
  let eventTypes = @["telemetry", "alert", "advisory", "heartbeat"]
  let priorities = @[epCritical, epHigh, epNormal, epLow]

  for i in 0 ..< 200:
    let event = DroneEvent(
      droneId: fmt"D-{i mod 20:04d}",
      eventType: eventTypes[rng.rand(eventTypes.high)],
      priority: priorities[rng.rand(priorities.high)],
      timestamp: float64(i) * 0.1,
      data: {"step": $i}.toTable
    )
    dispatcher.publish(event)

  let processed = await dispatcher.dispatch()
  let stats = dispatcher.getStats()

  echo fmt"=== Async Dispatcher Stats ==="
  echo fmt"  Dispatched: {stats.totalDispatched}"
  echo fmt"  Dropped:    {stats.totalDropped}"
  echo fmt"  Processed:  {processed}"

when isMainModule:
  waitFor simulateDispatcher()
