;;; Phase 599: symbolic_planner — Common Lisp 기반 군집 드론 기호 계획 시스템
;;; SDACS Symbolic Mission Planner

(defpackage :sdacs-planner
  (:use :common-lisp)
  (:export :make-drone-state :make-mission :plan-mission :print-plan))

(in-package :sdacs-planner)

;; 드론 상태 구조체 (defstruct 사용)
(defstruct drone-state
  (id 0 :type integer)
  (latitude 0.0 :type double-float)
  (longitude 0.0 :type double-float)
  (altitude 0.0 :type double-float)
  (battery 100.0 :type double-float)
  (is-armed nil :type boolean)
  (flight-mode "STABILIZE" :type string))

;; 웨이포인트 구조체 (defstruct 사용)
(defstruct waypoint
  (lat 0.0 :type double-float)
  (lon 0.0 :type double-float)
  (alt 30.0 :type double-float)
  (speed 5.0 :type double-float)
  (hold-time 0 :type integer))

;; 미션 액션 타입
(defstruct mission-action
  (type :goto :type keyword)
  (drone-ids nil :type list)
  (params nil :type list))

;; 미션 구조체 (defstruct 사용)
(defstruct mission
  (name "" :type string)
  (drone-ids nil :type list)
  (waypoints nil :type list)
  (actions nil :type list)
  (priority 1 :type integer))

;; 거리 계산 (위도/경도 → 미터)
(defun haversine-distance (lat1 lon1 lat2 lon2)
  "두 점 사이의 거리를 미터로 계산 (근사값)"
  (let* ((r 6371000.0d0)
         (dlat (* (/ (- lat2 lat1) 180.0d0) pi))
         (dlon (* (/ (- lon2 lon1) 180.0d0) pi))
         (a (+ (expt (sin (/ dlat 2.0d0)) 2.0d0)
               (* (cos (* (/ lat1 180.0d0) pi))
                  (cos (* (/ lat2 180.0d0) pi))
                  (expt (sin (/ dlon 2.0d0)) 2.0d0)))))
    (* r 2.0d0 (atan (sqrt a) (sqrt (- 1.0d0 a))))))

;; 웨이포인트 순서 최적화 (그리디 TSP)
(defun optimize-waypoint-order (waypoints)
  "그리디 알고리즘으로 웨이포인트 방문 순서 최적화"
  (when (null waypoints) (return-from optimize-waypoint-order nil))
  (let ((remaining (copy-list waypoints))
        (ordered nil)
        (current (first waypoints)))
    (push current ordered)
    (setf remaining (remove current remaining))
    (loop while remaining do
      (let ((nearest (first remaining))
            (min-dist most-positive-double-float))
        (dolist (wp remaining)
          (let ((dist (haversine-distance
                       (waypoint-lat current) (waypoint-lon current)
                       (waypoint-lat wp) (waypoint-lon wp))))
            (when (< dist min-dist)
              (setf min-dist dist
                    nearest wp))))
        (push nearest ordered)
        (setf remaining (remove nearest remaining))
        (setf current nearest)))
    (nreverse ordered)))

;; 미션 계획 생성
(defun plan-mission (mission drone-states)
  "미션과 드론 상태를 입력받아 실행 계획 생성"
  (let ((optimized-wps (optimize-waypoint-order (mission-waypoints mission)))
        (plan nil))
    ;; 이륙 액션
    (push (make-mission-action
           :type :takeoff
           :drone-ids (mission-drone-ids mission)
           :params (list :alt 30.0))
          plan)
    ;; 웨이포인트 방문 액션
    (dolist (wp optimized-wps)
      (push (make-mission-action
             :type :goto
             :drone-ids (mission-drone-ids mission)
             :params (list :lat (waypoint-lat wp)
                           :lon (waypoint-lon wp)
                           :alt (waypoint-alt wp)
                           :speed (waypoint-speed wp)))
            plan))
    ;; 착륙 액션
    (push (make-mission-action
           :type :land
           :drone-ids (mission-drone-ids mission)
           :params nil)
          plan)
    (nreverse plan)))

;; 계획 출력
(defun print-plan (plan)
  "실행 계획을 사람이 읽을 수 있는 형식으로 출력"
  (format t "~%=== 미션 실행 계획 (Phase 599) ===~%")
  (loop for action in plan
        for i from 1
        do (format t "Step ~d: ~a drones=~a~%"
                   i
                   (mission-action-type action)
                   (mission-action-drone-ids action))))

;; 충돌 검사
(defun check-conflicts (drone-states min-separation)
  "드론 상태 목록에서 잠재적 충돌 감지"
  (let ((conflicts nil))
    (loop for i from 0 below (length drone-states) do
      (loop for j from (1+ i) below (length drone-states) do
        (let* ((d1 (nth i drone-states))
               (d2 (nth j drone-states))
               (dist (haversine-distance
                      (drone-state-latitude d1) (drone-state-longitude d1)
                      (drone-state-latitude d2) (drone-state-longitude d2))))
          (when (< dist min-separation)
            (push (list (drone-state-id d1) (drone-state-id d2) dist) conflicts)))))
    conflicts))

;; 메인 실행
(defun main ()
  (format t "SDACS Symbolic Planner — Phase 599~%")
  (let* ((wps (list (make-waypoint :lat 37.50d0 :lon 127.00d0 :alt 50.0d0)
                    (make-waypoint :lat 37.52d0 :lon 127.02d0 :alt 60.0d0)
                    (make-waypoint :lat 37.51d0 :lon 127.03d0 :alt 55.0d0)))
         (m (make-mission :name "patrol" :drone-ids '(0 1 2) :waypoints wps))
         (states (list (make-drone-state :id 0 :latitude 37.50d0 :longitude 127.00d0 :altitude 50.0d0)
                       (make-drone-state :id 1 :latitude 37.51d0 :longitude 127.01d0 :altitude 52.0d0)))
         (plan (plan-mission m states)))
    (print-plan plan)
    (let ((conflicts (check-conflicts states 5.0d0)))
      (format t "충돌 감지: ~d건~%" (length conflicts)))))

(main)
