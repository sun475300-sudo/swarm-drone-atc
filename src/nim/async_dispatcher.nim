# Async dispatcher stub for SDACS event queue — Nim
import asyncdispatch, tables, deques

type
  EventKind* = enum
    ekTelemetry, ekCommand, ekAlert

  Event* = object
    kind*: EventKind
    droneId*: string
    payload*: string

  AsyncDispatcher* = ref object
    handlers: Table[EventKind, seq[proc(e: Event): Future[void]]]
    queue: Deque[Event]

proc newAsyncDispatcher*(): AsyncDispatcher =
  AsyncDispatcher(handlers: initTable[EventKind, seq[proc(e: Event): Future[void]]](),
                  queue: initDeque[Event]())

proc on*(d: AsyncDispatcher; kind: EventKind; handler: proc(e: Event): Future[void]) =
  if kind notin d.handlers: d.handlers[kind] = @[]
  d.handlers[kind].add(handler)

proc dispatch*(d: AsyncDispatcher; e: Event): Future[void] {.async.} =
  if e.kind in d.handlers:
    for h in d.handlers[e.kind]: await h(e)
