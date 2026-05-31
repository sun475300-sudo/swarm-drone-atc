# Async Dispatcher — SDACS Phase 659
import asyncdispatch

type AsyncDispatcher* = ref object
  handlers: seq[proc()]

proc newAsyncDispatcher*(): AsyncDispatcher =
  AsyncDispatcher(handlers: @[])

proc dispatch*(d: AsyncDispatcher, handler: proc()) =
  d.handlers.add(handler)
