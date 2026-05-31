# async_dispatcher.nim - Async event dispatcher for SDACS
import std/[asyncdispatch, asyncnet, tables, sequtils, strformat]

type
  EventType* = enum
    evTelemetry, evConflict, evCommand, evHeartbeat, evAlert

  DroneEvent* = object
    event_type*: EventType
    drone_id*:   string
    payload*:    string
    timestamp*:  float

  HandlerProc* = proc(event: DroneEvent): Future[void] {.async.}

  AsyncDispatcher* = ref object
    handlers*:      Table[EventType, seq[HandlerProc]]
    event_queue*:   seq[DroneEvent]
    processed*:     int
    running*:       bool

proc newAsyncDispatcher*(): AsyncDispatcher =
  AsyncDispatcher(
    handlers:    initTable[EventType, seq[HandlerProc]](),
    event_queue: @[],
    processed:   0,
    running:     false
  )

proc subscribe*(d: AsyncDispatcher; event_type: EventType; handler: HandlerProc) =
  if event_type notin d.handlers:
    d.handlers[event_type] = @[]
  d.handlers[event_type].add(handler)

proc dispatch*(d: AsyncDispatcher; event: DroneEvent) {.async.} =
  if event.event_type in d.handlers:
    for handler in d.handlers[event.event_type]:
      await handler(event)
  inc d.processed

proc enqueue*(d: AsyncDispatcher; event: DroneEvent) =
  d.event_queue.add(event)

proc processQueue*(d: AsyncDispatcher) {.async.} =
  d.running = true
  while d.event_queue.len > 0:
    let event = d.event_queue[0]
    d.event_queue.delete(0)
    await d.dispatch(event)
  d.running = false

proc summary*(d: AsyncDispatcher): string =
  fmt"AsyncDispatcher: processed={d.processed}, queue={d.event_queue.len}, handlers={d.handlers.len}"
