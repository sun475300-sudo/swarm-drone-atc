# SDACS Async Dispatcher — Nim
# 군집드론 비동기 이벤트 디스패처

import std/[asyncdispatch, tables, strformat]

type
  EventKind = enum
    Telemetry, Command, Alert, Heartbeat

  DroneEvent = object
    kind: EventKind
    droneId: string
    payload: string
    timestamp: float

  HandlerProc = proc(event: DroneEvent): Future[void]

  AsyncDispatcher = ref object
    handlers: Table[EventKind, seq[HandlerProc]]
    queue: seq[DroneEvent]
    running: bool

proc newAsyncDispatcher(): AsyncDispatcher =
  AsyncDispatcher(
    handlers: initTable[EventKind, seq[HandlerProc]](),
    queue: @[],
    running: false
  )

proc on(d: AsyncDispatcher, kind: EventKind, handler: HandlerProc) =
  if not d.handlers.hasKey(kind):
    d.handlers[kind] = @[]
  d.handlers[kind].add(handler)

proc dispatch(d: AsyncDispatcher, event: DroneEvent) {.async.} =
  if d.handlers.hasKey(event.kind):
    for handler in d.handlers[event.kind]:
      await handler(event)

proc emit(d: AsyncDispatcher, event: DroneEvent) =
  d.queue.add(event)

proc processQueue(d: AsyncDispatcher) {.async.} =
  while d.queue.len > 0:
    let event = d.queue[0]
    d.queue.delete(0)
    await d.dispatch(event)

when isMainModule:
  let dispatcher = newAsyncDispatcher()

  dispatcher.on(Telemetry, proc(e: DroneEvent): Future[void] {.async.} =
    echo fmt"Telemetry from {e.droneId}: {e.payload}")

  dispatcher.emit(DroneEvent(
    kind: Telemetry,
    droneId: "DRONE-001",
    payload: "alt=100,bat=85",
    timestamp: 1234567890.0
  ))

  waitFor dispatcher.processQueue()
