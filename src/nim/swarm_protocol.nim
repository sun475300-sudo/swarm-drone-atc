# Phase 496: Swarm Communication Protocol (Nim)
# TDMA/CDMA 하이브리드 MAC, 우선순위 메시징, 값 타입 최적화

import std/[tables, algorithm, sequtils, strformat, math, hashes]

type
  MACProtocol* = enum
    mpTDMA, mpCDMA, mpCSMA, mpHybrid

  MessagePriority* = enum
    mpEmergency = 0, mpCollisionAvoid = 1, mpControl = 2,
    mpTelemetry = 3, mpStatus = 4, mpBulk = 5

  SwarmMessage* = object
    msgId*: string
    src*: int
    dst*: int  # -1 = broadcast
    priority*: MessagePriority
    payload*: seq[byte]
    timestamp*: float64
    ttl*: int
    hops*: int
    delivered*: bool

  TimeSlot* = object
    slotId*: int
    owner*: int
    startUs*: int
    durationUs*: int

  ChannelStats* = object
    throughputKbps*: float64
    latencyMs*: float64
    packetLoss*: float64
    collisions*: int
    msgSent*: int
    msgDelivered*: int

  TDMAScheduler* = object
    nDrones*: int
    frameDuration*: int
    slotDuration*: int
    slots*: seq[TimeSlot]

  WalshCDMA* = object
    nCodes*: int
    codes*: seq[seq[float64]]

  SwarmProtocol* = object
    nDrones*: int
    tdma*: TDMAScheduler
    cdma*: WalshCDMA
    macMode*: MACProtocol
    queues*: Table[int, seq[SwarmMessage]]
    delivered*: seq[SwarmMessage]
    stats*: ChannelStats
    timeUs*: int64
    msgCounter*: int
    seed: uint64

proc xorshift(s: var uint64): float64 =
  s = s xor (s shl 13)
  s = s xor (s shr 7)
  s = s xor (s shl 17)
  result = float64(s) / float64(high(uint64))

proc initTDMA*(nDrones: int, frameDuration: int = 10000): TDMAScheduler =
  let slotDur = frameDuration div max(nDrones, 1)
  var slots: seq[TimeSlot] = @[]
  for i in 0..<nDrones:
    slots.add(TimeSlot(slotId: i, owner: i, startUs: i * slotDur, durationUs: slotDur))
  TDMAScheduler(nDrones: nDrones, frameDuration: frameDuration,
                slotDuration: slotDur, slots: slots)

proc canTransmit*(sched: TDMAScheduler, droneId: int, timeUs: int64): bool =
  let offset = int(timeUs mod int64(sched.frameDuration))
  for slot in sched.slots:
    if slot.owner == droneId:
      if offset >= slot.startUs and offset < slot.startUs + slot.durationUs:
        return true
  return false

proc generateWalsh*(n: int): seq[seq[float64]] =
  if n == 1:
    return @[@[1.0]]
  let half = generateWalsh(n div 2)
  var full: seq[seq[float64]] = @[]
  for row in half:
    full.add(row & row)
  for row in half:
    let neg = row.mapIt(-it)
    full.add(row & neg)
  return full

proc initWalshCDMA*(nCodes: int = 8): WalshCDMA =
  WalshCDMA(nCodes: nCodes, codes: generateWalsh(nCodes))

proc encode*(cdma: WalshCDMA, data: seq[float64], codeIdx: int): seq[float64] =
  let code = cdma.codes[codeIdx mod cdma.nCodes]
  var encoded: seq[float64] = @[]
  for d in data:
    for c in code:
      encoded.add(d * c)
  return encoded

proc decode*(cdma: WalshCDMA, signal: seq[float64], codeIdx: int): seq[float64] =
  let code = cdma.codes[codeIdx mod cdma.nCodes]
  let n = code.len
  let chunks = signal.len div n
  var decoded: seq[float64] = @[]
  for i in 0..<chunks:
    var dot = 0.0
    for j in 0..<n:
      dot += signal[i * n + j] * code[j]
    decoded.add(dot / float64(n))
  return decoded

proc initSwarmProtocol*(nDrones: int = 20, seed: uint64 = 42): SwarmProtocol =
  var queues = initTable[int, seq[SwarmMessage]]()
  for i in 0..<nDrones:
    queues[i] = @[]
  SwarmProtocol(
    nDrones: nDrones,
    tdma: initTDMA(nDrones),
    cdma: initWalshCDMA(max(8, nDrones)),
    macMode: mpHybrid,
    queues: queues,
    delivered: @[],
    stats: ChannelStats(),
    timeUs: 0,
    msgCounter: 0,
    seed: seed
  )

proc send*(proto: var SwarmProtocol, src, dst: int,
           payload: seq[byte], priority: MessagePriority = mpTelemetry): SwarmMessage =
  proto.msgCounter += 1
  let msg = SwarmMessage(
    msgId: fmt"MSG-{proto.msgCounter:06d}",
    src: src, dst: dst, priority: priority,
    payload: payload,
    timestamp: float64(proto.timeUs) / 1e6,
    ttl: 5, hops: 0, delivered: false
  )
  proto.queues[src].add(msg)
  proto.stats.msgSent += 1
  return msg

proc tick*(proto: var SwarmProtocol, dtUs: int = 1000) =
  proto.timeUs += int64(dtUs)
  for droneId in 0..<proto.nDrones:
    if proto.queues[droneId].len == 0: continue
    proto.queues[droneId].sort(proc(a, b: SwarmMessage): int =
      cmp(ord(a.priority), ord(b.priority)))

    var toRemove: seq[int] = @[]
    for idx in 0..<min(3, proto.queues[droneId].len):
      var canSend = false
      let msg = proto.queues[droneId][idx]
      case proto.macMode
      of mpTDMA:
        canSend = proto.tdma.canTransmit(droneId, proto.timeUs)
      of mpCDMA:
        canSend = true
      of mpHybrid:
        if ord(msg.priority) <= ord(mpCollisionAvoid):
          canSend = true
        else:
          canSend = proto.tdma.canTransmit(droneId, proto.timeUs)
      of mpCSMA:
        canSend = xorshift(proto.seed) > 0.3

      if canSend:
        if xorshift(proto.seed) > proto.stats.packetLoss:
          var delivered = proto.queues[droneId][idx]
          delivered.delivered = true
          delivered.hops += 1
          proto.delivered.add(delivered)
          proto.stats.msgDelivered += 1
          toRemove.add(idx)
        else:
          proto.stats.collisions += 1

    for i in countdown(toRemove.len - 1, 0):
      proto.queues[droneId].delete(toRemove[i])

proc deliveryRate*(proto: SwarmProtocol): float64 =
  if proto.stats.msgSent == 0: return 1.0
  float64(proto.stats.msgDelivered) / float64(proto.stats.msgSent)

proc summary*(proto: SwarmProtocol): Table[string, string] =
  result = initTable[string, string]()
  result["protocol"] = $proto.macMode
  result["drones"] = $proto.nDrones
  result["sent"] = $proto.stats.msgSent
  result["delivered"] = $proto.stats.msgDelivered
  result["collisions"] = $proto.stats.collisions
  result["delivery_rate"] = fmt"{proto.deliveryRate():.4f}"
