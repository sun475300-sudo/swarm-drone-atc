# Phase 659 — Async Dispatcher (Nim)
# 군집 드론 텔레메트리 비동기 이벤트 디스패처

import asyncdispatch, asyncnet, json, tables, sets, strformat

type
  DroneSnapshot* = object
    id*:         string
    position*:   array[3, float]
    velocity*:   array[3, float]
    phase*:      string
    batteryPct*: float

  Client = ref object
    socket: AsyncSocket
    id:     string

  Dispatcher* = ref object
    clients:   Table[string, Client]
    snapshots: seq[DroneSnapshot]

proc newDispatcher*(): Dispatcher =
  Dispatcher(clients: initTable[string, Client]())

proc broadcast*(d: Dispatcher, payload: string) {.async.} =
  ## 연결된 모든 클라이언트에 JSON 페이로드를 전송한다.
  var dead: seq[string]
  for id, client in d.clients:
    try:
      await client.socket.send(payload & "\n")
    except:
      dead.add(id)
  for id in dead:
    d.clients.del(id)

proc handleClient*(d: Dispatcher, socket: AsyncSocket, clientId: string) {.async.} =
  let client = Client(socket: socket, id: clientId)
  d.clients[clientId] = client
  try:
    while true:
      let line = await socket.recvLine()
      if line.len == 0: break
  finally:
    socket.close()
    d.clients.del(clientId)

proc pushSnapshot*(d: Dispatcher, snap: DroneSnapshot) {.async.} =
  d.snapshots.add(snap)
  let payload = %* {
    "id":       snap.id,
    "pos":      snap.position,
    "vel":      snap.velocity,
    "phase":    snap.phase,
    "battery":  snap.batteryPct,
  }
  await d.broadcast($payload)

proc clientCount*(d: Dispatcher): int = d.clients.len
