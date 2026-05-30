# SDACS Realtime Scheduler — Nim
# 군집드론 실시간 스케줄러

import std/[times, tables, heapqueue, strformat]

# 태스크 우선순위 타입
type
  TaskPriority = enum
    Critical = 0
    High = 1
    Normal = 2
    Low = 3

  # 스케줄 태스크 타입
  ScheduledTask = ref object
    id: string
    priority: TaskPriority
    period: float        # 주기 (ms)
    nextRun: float       # 다음 실행 시각
    deadline: float      # 마감 시각
    execTime: float      # 예상 실행 시간 (ms)
    callback: proc()

  # RTScheduler — 실시간 스케줄러 메인 타입
  RTScheduler = ref object
    tasks: Table[string, ScheduledTask]
    running: bool
    tickRate: float      # Hz
    missedDeadlines: int
    completedTasks: int

# RTScheduler 생성자
proc newRTScheduler(tickRate: float = 1000.0): RTScheduler =
  RTScheduler(
    tasks: initTable[string, ScheduledTask](),
    running: false,
    tickRate: tickRate,
    missedDeadlines: 0,
    completedTasks: 0
  )

# 태스크 등록
proc addTask(scheduler: RTScheduler, id: string, priority: TaskPriority,
             period: float, execTime: float, callback: proc()) =
  let task = ScheduledTask(
    id: id,
    priority: priority,
    period: period,
    nextRun: 0.0,
    deadline: period,
    execTime: execTime,
    callback: callback
  )
  scheduler.tasks[id] = task
  echo fmt"Task registered: {id} (priority={priority}, period={period}ms)"

# 태스크 제거
proc removeTask(scheduler: RTScheduler, id: string) =
  if scheduler.tasks.hasKey(id):
    scheduler.tasks.del(id)
    echo fmt"Task removed: {id}"

# CPU 사용률 계산
proc cpuUtilization(scheduler: RTScheduler): float =
  var total = 0.0
  for _, task in scheduler.tasks:
    total += task.execTime / task.period
  return total * 100.0

# 실행 가능성 검사 (Rate Monotonic)
proc isSchedulable(scheduler: RTScheduler): bool =
  let n = scheduler.tasks.len
  if n == 0: return true
  let bound = float(n) * (pow(2.0, 1.0 / float(n)) - 1.0)
  return scheduler.cpuUtilization() <= bound * 100.0

# 스케줄러 상태 출력
proc status(scheduler: RTScheduler) =
  echo fmt"RTScheduler Status:"
  echo fmt"  Tasks: {scheduler.tasks.len}"
  echo fmt"  CPU Utilization: {scheduler.cpuUtilization():.2f}%"
  echo fmt"  Schedulable: {scheduler.isSchedulable()}"
  echo fmt"  Missed Deadlines: {scheduler.missedDeadlines}"
  echo fmt"  Completed: {scheduler.completedTasks}"

# 메인 실행
when isMainModule:
  let scheduler = newRTScheduler(1000.0)

  scheduler.addTask("SensorRead", Critical, 10.0, 0.5, proc() =
    echo "Reading sensors...")
  scheduler.addTask("NavUpdate", High, 100.0, 5.0, proc() =
    echo "Updating navigation...")
  scheduler.addTask("TelemetryTx", Normal, 200.0, 10.0, proc() =
    echo "Transmitting telemetry...")
  scheduler.addTask("Logger", Low, 1000.0, 20.0, proc() =
    echo "Logging data...")

  scheduler.status()
