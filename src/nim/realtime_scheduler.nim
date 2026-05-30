# Phase 593: realtime_scheduler — Nim 기반 실시간 스케줄러
# SDACS Real-Time Task Scheduler for Drone Control Loops

import times, strformat, math, algorithm, sequtils

# 실시간 태스크 우선순위
type
  TaskPriority = enum
    tpBackground = 0
    tpLow        = 1
    tpNormal     = 5
    tpHigh       = 10
    tpCritical   = 20

  TaskState = enum
    tsReady, tsRunning, tsBlocked, tsCompleted

  # 실시간 태스크 정의
  RTTask = ref object
    id          : int
    name        : string
    priority    : TaskPriority
    periodMs    : float        # 주기 (ms)
    deadlineMs  : float        # 데드라인 (ms)
    executionMs : float        # 실행 시간 추정 (ms)
    state       : TaskState
    nextRunAt   : float        # 다음 실행 시각 (ms)
    runCount    : int
    missedDeadlines : int

  # RTScheduler 클래스
  RTScheduler* = ref object
    tasks        : seq[RTTask]
    currentTimeMs: float
    schedulerLog : seq[string]
    algorithm    : string

proc newRTScheduler*(algorithm: string = "EDF"): RTScheduler =
  RTScheduler(
    tasks         = @[],
    currentTimeMs = 0.0,
    schedulerLog  = @[],
    algorithm     = algorithm
  )

proc addTask*(sched: RTScheduler, id: int, name: string, priority: TaskPriority,
              periodMs, deadlineMs, execMs: float) =
  let task = RTTask(
    id            : id,
    name          : name,
    priority      : priority,
    periodMs      : periodMs,
    deadlineMs    : deadlineMs,
    executionMs   : execMs,
    state         : tsReady,
    nextRunAt     : 0.0,
    runCount      : 0,
    missedDeadlines: 0
  )
  sched.tasks.add(task)

# EDF (Earliest Deadline First) 스케줄링
proc edfSelectTask(sched: RTScheduler): RTTask =
  var readyTasks = sched.tasks.filterIt(
    it.state == tsReady and it.nextRunAt <= sched.currentTimeMs
  )
  if readyTasks.len == 0:
    return nil
  # 가장 빠른 데드라인 태스크 선택
  readyTasks.sort(proc(a, b: RTTask): int =
    cmp(a.nextRunAt + a.deadlineMs, b.nextRunAt + b.deadlineMs)
  )
  readyTasks[0]

# RM (Rate Monotonic) 스케줄링
proc rmSelectTask(sched: RTScheduler): RTTask =
  var readyTasks = sched.tasks.filterIt(
    it.state == tsReady and it.nextRunAt <= sched.currentTimeMs
  )
  if readyTasks.len == 0:
    return nil
  # 가장 짧은 주기 태스크 선택 (우선순위 = 1/주기)
  readyTasks.sort(proc(a, b: RTTask): int = cmp(a.periodMs, b.periodMs))
  readyTasks[0]

# 태스크 실행 시뮬레이션
proc executeTask(sched: RTScheduler, task: RTTask) =
  let absoluteDeadline = task.nextRunAt + task.deadlineMs
  let completionTime   = sched.currentTimeMs + task.executionMs

  task.state   = tsRunning
  task.runCount += 1

  if completionTime > absoluteDeadline:
    task.missedDeadlines += 1
    sched.schedulerLog.add(&"  [MISS] {task.name} 데드라인 초과 ({completionTime:.1f} > {absoluteDeadline:.1f})")
  else:
    sched.schedulerLog.add(&"  [OK]   {task.name} 완료 ({completionTime:.1f}ms)")

  # 다음 실행 시각 설정
  task.nextRunAt = task.nextRunAt + task.periodMs
  task.state = tsReady

# 스케줄러 실행 (n 사이클)
proc run*(sched: RTScheduler, durationMs: float, dtMs: float = 1.0) =
  echo &"RTScheduler 알고리즘: {sched.algorithm}"
  while sched.currentTimeMs < durationMs:
    let selected = case sched.algorithm:
      of "EDF": edfSelectTask(sched)
      of "RM":  rmSelectTask(sched)
      else:     edfSelectTask(sched)

    if selected != nil:
      executeTask(sched, selected)

    sched.currentTimeMs += dtMs

# CPU 이용률 계산 (Liu & Layland 공식)
proc cpuUtilization*(sched: RTScheduler): float =
  result = 0.0
  for t in sched.tasks:
    result += t.executionMs / t.periodMs

# 스케줄 가능성 검증 (RM 이론적 한계: n*(2^(1/n)-1))
proc isSchedulable*(sched: RTScheduler): bool =
  let n = sched.tasks.len.float
  if n == 0: return true
  let util = cpuUtilization(sched)
  let limit = n * (pow(2.0, 1.0 / n) - 1.0)
  util <= limit

proc summary*(sched: RTScheduler): string =
  let totalMissed = sched.tasks.mapIt(it.missedDeadlines).foldl(a + b, 0)
  let totalRuns   = sched.tasks.mapIt(it.runCount).foldl(a + b, 0)
  &"tasks={sched.tasks.len} runs={totalRuns} missed={totalMissed} util={cpuUtilization(sched):.3f}"

when isMainModule:
  echo "SDACS Real-Time Scheduler — Phase 593\n"

  var sched = newRTScheduler("EDF")

  # 드론 제어 루프 태스크 등록
  sched.addTask(0, "attitude_ctrl",   tpCritical, 10.0,  10.0, 1.0)   # 100Hz 자세 제어
  sched.addTask(1, "position_ctrl",   tpHigh,     100.0, 100.0, 5.0)  # 10Hz 위치 제어
  sched.addTask(2, "telemetry_send",  tpNormal,   200.0, 200.0, 8.0)  # 5Hz 텔레메트리
  sched.addTask(3, "battery_monitor", tpNormal,   500.0, 500.0, 2.0)  # 2Hz 배터리 모니터
  sched.addTask(4, "log_write",       tpLow,     1000.0, 1000.0, 10.0)# 1Hz 로그

  echo &"CPU 이용률: {cpuUtilization(sched):.3f}"
  echo &"스케줄 가능: {isSchedulable(sched)}"

  sched.run(durationMs = 50.0, dtMs = 5.0)

  echo "\n스케줄 이벤트:"
  for entry in sched.schedulerLog:
    echo entry

  echo &"\n요약: {summary(sched)}"
  echo "실시간 스케줄러 완료."
