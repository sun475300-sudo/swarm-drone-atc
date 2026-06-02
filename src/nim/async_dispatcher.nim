# Phase 649: Async Dispatcher — Nim
# SDACS async event dispatcher for drone command processing

import std/[asyncdispatch, tables, strformat, times]

type
  CommandType* = enum
    cmdTakeoff, cmdLand, cmdGoto, cmdRTL, cmdHold, cmdSetSpeed

  DroneCommand* = object
    drone_id*: string
    cmd_type*: CommandType
    params*:   Table[string, float]
    issued_at*: float

  CommandResult* = object
    success*:   bool
    message*:   string
    latency_ms*: float

  AsyncDispatcher* = ref object
    handlers*:    Table[CommandType, proc(cmd: DroneCommand): Future[CommandResult] {.async.}]
    queue_size*:  int
    dispatched*:  int
    failed*:      int

proc newAsyncDispatcher*(): AsyncDispatcher =
  AsyncDispatcher(
    handlers:   initTable[CommandType, proc(cmd: DroneCommand): Future[CommandResult] {.async.}](),
    queue_size: 0,
    dispatched: 0,
    failed:     0,
  )

proc register*(dispatcher: AsyncDispatcher, cmd_type: CommandType,
               handler: proc(cmd: DroneCommand): Future[CommandResult] {.async.}) =
  dispatcher.handlers[cmd_type] = handler

proc dispatch*(dispatcher: AsyncDispatcher, cmd: DroneCommand): Future[CommandResult] {.async.} =
  if cmd.cmd_type notin dispatcher.handlers:
    dispatcher.failed += 1
    return CommandResult(success: false, message: "No handler registered for " & $cmd.cmd_type)

  let t0 = epochTime()
  try:
    let result = await dispatcher.handlers[cmd.cmd_type](cmd)
    dispatcher.dispatched += 1
    return CommandResult(
      success:    result.success,
      message:    result.message,
      latency_ms: (epochTime() - t0) * 1000,
    )
  except Exception as e:
    dispatcher.failed += 1
    return CommandResult(success: false, message: e.msg)

proc dispatchBatch*(dispatcher: AsyncDispatcher, cmds: seq[DroneCommand]): Future[seq[CommandResult]] {.async.} =
  var futures = newSeq[Future[CommandResult]]()
  for cmd in cmds:
    futures.add(dispatcher.dispatch(cmd))
  result = await all(futures)

proc stats*(dispatcher: AsyncDispatcher): string =
  fmt"Dispatcher(dispatched={dispatcher.dispatched} failed={dispatcher.failed} handlers={dispatcher.handlers.len})"

proc defaultTakeoffHandler(cmd: DroneCommand): Future[CommandResult] {.async.} =
  let alt = cmd.params.getOrDefault("alt", 60.0)
  await sleepAsync(1)  # simulate async op
  return CommandResult(success: true, message: fmt"Drone {cmd.drone_id} taking off to {alt}m")

when isMainModule:
  proc main() {.async.} =
    let dispatcher = newAsyncDispatcher()
    dispatcher.register(cmdTakeoff, defaultTakeoffHandler)

    let cmd = DroneCommand(
      drone_id: "D001",
      cmd_type: cmdTakeoff,
      params:   {"alt": 60.0}.toTable,
      issued_at: epochTime(),
    )
    let result = await dispatcher.dispatch(cmd)
    echo fmt"Phase 649: {result.message} (latency={result.latency_ms:.1f}ms)"
    echo dispatcher.stats()

  waitFor main()
