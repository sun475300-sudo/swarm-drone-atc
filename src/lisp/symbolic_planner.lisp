;;;; SDACS Symbolic Planner — Common Lisp
;;;; 드론 공역 제어를 위한 기호 계획 시스템

(defpackage :sdacs-planner
  (:use :cl)
  (:export #:drone-state #:make-drone-state
           #:plan-maneuver #:find-safe-altitude
           #:conflict-p #:priority-order))

(in-package :sdacs-planner)

;;; Data structures

(defstruct drone-state
  (id "" :type string)
  (x 0.0 :type float)
  (y 0.0 :type float)
  (z 0.0 :type float)
  (vx 0.0 :type float)
  (vy 0.0 :type float)
  (vz 0.0 :type float)
  (priority 1 :type integer)
  (battery 100.0 :type float))

(defstruct maneuver
  (type :maintain)
  (target-x 0.0 :type float)
  (target-y 0.0 :type float)
  (target-z 0.0 :type float)
  (urgency 0.0 :type float))

;;; Utility functions

(defun distance-3d (a b)
  "Euclidean distance between two drone-states."
  (sqrt (+ (expt (- (drone-state-x b) (drone-state-x a)) 2)
           (expt (- (drone-state-y b) (drone-state-y a)) 2)
           (expt (- (drone-state-z b) (drone-state-z a)) 2))))

(defun conflict-p (a b &optional (threshold 50.0))
  "Return T if two drones are within conflict threshold."
  (< (distance-3d a b) threshold))

(defun time-to-cpa (a b)
  "Approximate time to closest point of approach."
  (let* ((dx (- (drone-state-x b) (drone-state-x a)))
         (dy (- (drone-state-y b) (drone-state-y a)))
         (dvx (- (drone-state-vx b) (drone-state-vx a)))
         (dvy (- (drone-state-vy b) (drone-state-vy a)))
         (dv-sq (+ (* dvx dvx) (* dvy dvy))))
    (if (< dv-sq 1e-6)
        most-positive-double-float
        (max 0.0 (- (/ (+ (* dx dvx) (* dy dvy)) dv-sq))))))

;;; Planning rules

(defun priority-order (drones)
  "Sort drones by priority (higher = first)."
  (sort (copy-list drones)
        #'> :key #'drone-state-priority))

(defun find-safe-altitude (drone obstacles &optional (step 10.0) (max-alt 500.0))
  "Find nearest altitude with no conflicts."
  (let ((z (drone-state-z drone)))
    (loop for alt from z to max-alt by step
          for test-drone = (copy-structure drone)
          do (setf (drone-state-z test-drone) alt)
          unless (some (lambda (obs) (conflict-p test-drone obs)) obstacles)
            return alt
          finally (return max-alt))))

(defun plan-maneuver (drone threats)
  "Produce a symbolic maneuver plan for drone given list of threats."
  (cond
    ((null threats)
     (make-maneuver :type :maintain
                    :target-x (drone-state-x drone)
                    :target-y (drone-state-y drone)
                    :target-z (drone-state-z drone)
                    :urgency 0.0))
    (t
     (let* ((nearest (first (sort (copy-list threats)
                                  #'< :key (lambda (t2) (distance-3d drone t2)))))
            (dist (distance-3d drone nearest))
            (urgency (max 0.0 (min 1.0 (- 1.0 (/ dist 50.0)))))
            (safe-z (find-safe-altitude drone threats)))
       (make-maneuver :type :climb
                      :target-x (drone-state-x drone)
                      :target-y (drone-state-y drone)
                      :target-z safe-z
                      :urgency urgency)))))

;;; Rule-based airspace classifier

(defun airspace-class (altitude)
  "Classify airspace by altitude (meters AGL)."
  (cond
    ((< altitude 50)   :class-g-low)
    ((< altitude 120)  :class-g)
    ((< altitude 300)  :class-e)
    ((< altitude 600)  :class-d)
    (t                 :class-c)))

(defun allowed-p (drone)
  "Check if drone is in allowed operational envelope."
  (and (<= (drone-state-z drone) 400.0)
       (>= (drone-state-battery drone) 20.0)))
