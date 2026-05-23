## Phase 346: Nim Game Theory Engine
## Iterated prisoner's dilemma + Nash equilibrium search.
## Value types, deterministic strategies.

import std/[math, sequtils, strformat, tables, algorithm]

type
  Strategy* = enum
    AlwaysCooperate, AlwaysDefect, TitForTat,
    Pavlov, Random, GrimTrigger

  Action* = enum
    Cooperate, Defect

  Player* = object
    playerId*: string
    strategy*: Strategy
    totalPayoff*: float64
    gamesPlayed*: int
    coopCount*: int
    history*: seq[Action]

  GameResult* = object
    playerA*, playerB*: string
    actionA*, actionB*: Action
    payoffA*, payoffB*: float64
    round*: int

  NashEquilibrium* = object
    stratA*, stratB*: Action
    payoffA*, payoffB*: float64
    isParetoOptimal*: bool

  GameTheoryEngine* = object
    players*: Table[string, Player]
    results*: seq[GameResult]
    roundNum*: int
    # Payoff matrix: (CC, CD, DC, DD)
    payoffCC*: tuple[a, b: float64]
    payoffCD*: tuple[a, b: float64]
    payoffDC*: tuple[a, b: float64]
    payoffDD*: tuple[a, b: float64]

# ── Payoff Lookup ────────────────────────────────────────────────
proc getPayoff(engine: GameTheoryEngine, a, b: Action): tuple[a, b: float64] =
  case a
  of Cooperate:
    case b
    of Cooperate: engine.payoffCC
    of Defect: engine.payoffCD
  of Defect:
    case b
    of Cooperate: engine.payoffDC
    of Defect: engine.payoffDD

# ── Init ─────────────────────────────────────────────────────────
proc newPrisonersDilemma*(): GameTheoryEngine =
  result = GameTheoryEngine(
    players: initTable[string, Player](),
    results: @[],
    roundNum: 0,
    payoffCC: (3.0, 3.0),
    payoffCD: (0.0, 5.0),
    payoffDC: (5.0, 0.0),
    payoffDD: (1.0, 1.0),
  )

proc newStagHunt*(): GameTheoryEngine =
  result = GameTheoryEngine(
    players: initTable[string, Player](),
    results: @[],
    roundNum: 0,
    payoffCC: (4.0, 4.0),
    payoffCD: (0.0, 3.0),
    payoffDC: (3.0, 0.0),
    payoffDD: (2.0, 2.0),
  )

proc addPlayer*(engine: var GameTheoryEngine, id: string, strategy: Strategy) =
  engine.players[id] = Player(
    playerId: id, strategy: strategy,
    totalPayoff: 0, gamesPlayed: 0, coopCount: 0, history: @[])

# ── Strategy Selection ───────────────────────────────────────────
proc chooseAction(player: Player, oppHistory: seq[Action], seed: int): Action =
  case player.strategy
  of AlwaysCooperate: Cooperate
  of AlwaysDefect: Defect
  of TitForTat:
    if oppHistory.len == 0: Cooperate
    else: oppHistory[^1]
  of Pavlov:
    if player.history.len == 0: Cooperate
    elif player.history[^1] == Cooperate and oppHistory.len > 0 and oppHistory[^1] == Cooperate: Cooperate
    elif player.history[^1] == Defect and oppHistory.len > 0 and oppHistory[^1] == Defect: Cooperate
    else: Defect
  of GrimTrigger:
    if oppHistory.anyIt(it == Defect): Defect
    else: Cooperate
  of Random:
    if (seed mod 2) == 0: Cooperate else: Defect

# ── Play Round ───────────────────────────────────────────────────
proc playRound*(engine: var GameTheoryEngine, aId, bId: string): GameResult =
  engine.roundNum += 1
  var a = engine.players[aId]
  var b = engine.players[bId]

  let actA = chooseAction(a, b.history, engine.roundNum * 7 + aId.len)
  let actB = chooseAction(b, a.history, engine.roundNum * 13 + bId.len)
  let payoff = engine.getPayoff(actA, actB)

  a.totalPayoff += payoff.a
  b.totalPayoff += payoff.b
  a.gamesPlayed += 1
  b.gamesPlayed += 1
  a.history.add(actA)
  b.history.add(actB)
  if actA == Cooperate: a.coopCount += 1
  if actB == Cooperate: b.coopCount += 1

  engine.players[aId] = a
  engine.players[bId] = b

  result = GameResult(
    playerA: aId, playerB: bId,
    actionA: actA, actionB: actB,
    payoffA: payoff.a, payoffB: payoff.b,
    round: engine.roundNum)
  engine.results.add(result)

# ── Tournament ───────────────────────────────────────────────────
proc tournament*(engine: var GameTheoryEngine, nRounds: int): Table[string, float64] =
  let ids = engine.players.keys.toSeq
  for _ in 0..<nRounds:
    for i in 0..<ids.len:
      for j in i+1..<ids.len:
        discard engine.playRound(ids[i], ids[j])
  result = initTable[string, float64]()
  for id, p in engine.players:
    result[id] = p.totalPayoff

# ── Nash Equilibria ──────────────────────────────────────────────
proc findNash*(engine: GameTheoryEngine): seq[NashEquilibrium] =
  result = @[]
  for a1 in [Cooperate, Defect]:
    for a2 in [Cooperate, Defect]:
      let p = engine.getPayoff(a1, a2)
      var isNash = true
      # Check if A can improve
      for alt in [Cooperate, Defect]:
        let altP = engine.getPayoff(alt, a2)
        if altP.a > p.a:
          isNash = false; break
      if isNash:
        for alt in [Cooperate, Defect]:
          let altP = engine.getPayoff(a1, alt)
          if altP.b > p.b:
            isNash = false; break
      if isNash:
        # Pareto check
        var pareto = true
        for aa in [Cooperate, Defect]:
          for bb in [Cooperate, Defect]:
            let q = engine.getPayoff(aa, bb)
            if q.a >= p.a and q.b >= p.b and (q.a > p.a or q.b > p.b):
              pareto = false
        result.add(NashEquilibrium(stratA: a1, stratB: a2,
          payoffA: p.a, payoffB: p.b, isParetoOptimal: pareto))

proc summary*(engine: GameTheoryEngine): string =
  let totalPayoff = engine.players.values.toSeq.mapIt(it.totalPayoff).foldl(a + b, 0.0)
  fmt"Players: {engine.players.len} | Rounds: {engine.roundNum} | SocialWelfare: {totalPayoff:.1f}"

when isMainModule:
  var engine = newPrisonersDilemma()
  engine.addPlayer("tft", TitForTat)
  engine.addPlayer("coop", AlwaysCooperate)
  engine.addPlayer("defect", AlwaysDefect)
  engine.addPlayer("pavlov", Pavlov)
  engine.addPlayer("grim", GrimTrigger)

  let scores = engine.tournament(20)
  for id in scores.keys.toSeq.sorted:
    echo fmt"  {id}: {scores[id]:.0f}"

  let nash = engine.findNash()
  echo fmt"\nNash equilibria: {nash.len}"
  for eq in nash:
    echo fmt"  ({eq.stratA}, {eq.stratB}) → ({eq.payoffA}, {eq.payoffB}) Pareto: {eq.isParetoOptimal}"
  echo engine.summary()
