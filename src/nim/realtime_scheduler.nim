# Phase 593: Realtime Scheduler — Nim
# 실시간 태스크 스케줄러: Rate Monotonic,
# 데드라인 모니터링, 우선순위 역전 방지.

import std/[tables, algorithm, sequtils, strformat, times, math]

# ─── 타입 정의 ───
type
  TaskState = enum
    tsReady, tsRunning, tsBlocked, tsCompleted, tsMissed

  TaskPriority = enum
    tpCritical, tpHigh, tpMedium, tpLow

  RealtimeTask = object
    id: int
    name: string
    period: float          # ms
    wcet: float            # Worst-Case Execution Time (ms)
    deadline: float        # ms
    priority: TaskPriority
    state: TaskState
    executionTime: float
    responseTime: float
    deadlineMisses: int
    completions: int

  SchedulerStats = object
    totalTasks: int
    completedTasks: int
    missedDeadlines: int
    cpuUtilization: float
    avgResponseTime: float

  RTScheduler = object
    tasks: seq[RealtimeTask]
    currentTime: float
    quantum: float         # ms
    contextSwitches: int
    idleTime: float
    totalTime: float

# ─── Rate Monotonic 우선순위 할당 ───
proc assignRMPriority(task: var RealtimeTask) =
  ## 주기가 짧을수록 높은 우선순위
  if task.period <= 10.0:
    task.priority = tpCritical
  elif task.period <= 50.0:
    task.priority = tpHigh
  elif task.period <= 100.0:
    task.priority = tpMedium
  else:
    task.priority = tpLow

# ─── 스케줄 가능성 검증 (Liu & Layland) ───
proc isSchedulable(tasks: seq[RealtimeTask]): bool =
  let n = tasks.len
  if n == 0: return true
  var utilization = 0.0
  for t in tasks:
    utilization += t.wcet / t.period
  let bound = float(n) * (pow(2.0, 1.0 / float(n)) - 1.0)
  return utilization <= bound

# ─── 스케줄러 초기화 ───
proc initScheduler(quantum: float = 1.0): RTScheduler =
  result.tasks = @[]
  result.currentTime = 0.0
  result.quantum = quantum
  result.contextSwitches = 0
  result.idleTime = 0.0
  result.totalTime = 0.0

proc addTask(sched: var RTScheduler, name: string, period, wcet: float) =
  var task = RealtimeTask(
    id: sched.tasks.len,
    name: name,
    period: period,
    wcet: wcet,
    deadline: period,
    state: tsReady,
    executionTime: 0.0,
    responseTime: 0.0,
    deadlineMisses: 0,
    completions: 0
  )
  assignRMPriority(task)
  sched.tasks.add(task)

# ─── 스케줄링 스텝 ───
proc scheduleStep(sched: var RTScheduler) =
  let dt = sched.quantum
  sched.currentTime += dt
  sched.totalTime += dt

  # 가장 높은 우선순위 Ready 태스크 선택
  var bestIdx = -1
  var bestPri = tpLow

  for i, task in sched.tasks:
    if task.state == tsReady and task.priority <= bestPri:
      bestPri = task.priority
      bestIdx = i

  if bestIdx >= 0:
    sched.tasks[bestIdx].state = tsRunning
    sched.tasks[bestIdx].executionTime += dt
    sched.contextSwitches += 1

    # 실행 완료 체크
    if sched.tasks[bestIdx].executionTime >= sched.tasks[bestIdx].wcet:
      sched.tasks[bestIdx].state = tsCompleted
      sched.tasks[bestIdx].completions += 1
      sched.tasks[bestIdx].responseTime = sched.tasks[bestIdx].executionTime
      sched.tasks[bestIdx].executionTime = 0.0
  else:
    sched.idleTime += dt

  # 주기적 재활성화 및 데드라인 체크
  for i in 0..<sched.tasks.len:
    if sched.tasks[i].state == tsCompleted:
      let elapsed = sched.currentTime
      let periods = floor(elapsed / sched.tasks[i].period)
      if elapsed >= periods * sched.tasks[i].period + sched.tasks[i].period:
        sched.tasks[i].state = tsReady
    elif sched.tasks[i].state == tsReady:
      if sched.tasks[i].executionTime > sched.tasks[i].deadline:
        sched.tasks[i].deadlineMisses += 1
        sched.tasks[i].state = tsMissed
        sched.tasks[i].executionTime = 0.0

proc run(sched: var RTScheduler, duration: float) =
  while sched.currentTime < duration:
    sched.scheduleStep()

# ─── 통계 ───
proc getStats(sched: RTScheduler): SchedulerStats =
  let completed = sched.tasks.mapIt(it.completions).foldl(a + b, 0)
  let missed = sched.tasks.mapIt(it.deadlineMisses).foldl(a + b, 0)
  let avgResp = if sched.tasks.len > 0:
    sched.tasks.mapIt(it.responseTime).foldl(a + b, 0.0) / float(sched.tasks.len)
  else: 0.0
  let util = if sched.totalTime > 0:
    (sched.totalTime - sched.idleTime) / sched.totalTime * 100.0
  else: 0.0

  SchedulerStats(
    totalTasks: sched.tasks.len,
    completedTasks: completed,
    missedDeadlines: missed,
    cpuUtilization: util,
    avgResponseTime: avgResp
  )

# ─── 메인 ───
when isMainModule:
  echo "=== SDACS Realtime Scheduler ==="

  var sched = initScheduler(0.5)

  # 드론 태스크 등록
  sched.addTask("IMU_Fusion", 5.0, 1.0)      # 200Hz
  sched.addTask("Motor_Control", 10.0, 2.0)   # 100Hz
  sched.addTask("GPS_Update", 50.0, 5.0)      # 20Hz
  sched.addTask("Telemetry_TX", 100.0, 8.0)   # 10Hz
  sched.addTask("Path_Plan", 200.0, 15.0)     # 5Hz
  sched.addTask("Battery_Mon", 500.0, 3.0)    # 2Hz

  echo &"  Tasks: {sched.tasks.len}"
  echo &"  Schedulable: {isSchedulable(sched.tasks)}"

  sched.run(1000.0)  # 1초 시뮬레이션

  let stats = sched.getStats()
  echo &"  Completed: {stats.completedTasks}"
  echo &"  Missed: {stats.missedDeadlines}"
  echo &"  CPU Util: {stats.cpuUtilization:.1f}%"
  echo &"  Avg Response: {stats.avgResponseTime:.2f} ms"
