# Phase 659 — Async Event Dispatcher in Nim
import asyncdispatch, tables, sequtils

type
  EventKind = enum
    Telemetry, Conflict, Resolution, Alert
  Event = object
    kind: EventKind
    droneId: string
    payload: string
  Handler = proc(e: Event): Future[void] {.async.}

var handlers = initTable[EventKind, seq[Handler]]()

proc on(kind: EventKind, h: Handler) =
  if kind notin handlers:
    handlers[kind] = @[]
  handlers[kind].add(h)

proc emit(e: Event) {.async.} =
  if e.kind in handlers:
    for h in handlers[e.kind]:
      await h(e)

proc dispatch(events: seq[Event]) {.async.} =
  for e in events:
    await emit(e)

when isMainModule:
  on(Conflict) do (e: Event) {.async.}:
    echo "Conflict detected: ", e.droneId, " — ", e.payload
  waitFor dispatch(@[
    Event(kind: Conflict, droneId: "D001", payload: "separation 25m")
  ])
