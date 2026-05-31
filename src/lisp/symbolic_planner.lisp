;;; Phase 599 — Common Lisp symbolic planner with defstruct
;;; SDACS symbolic AI planner for drone mission planning

(in-package :cl-user)

;;; ---- Domain structures ----

(defstruct drone-state
  "Represents the state of a single drone in the world model."
  (id        0     :type integer)
  (x         0.0d0 :type double-float)
  (y         0.0d0 :type double-float)
  (z         0.0d0 :type double-float)
  (battery   100.0 :type single-float)
  (status    :idle :type keyword))

(defstruct waypoint
  "A 3D navigation waypoint for the planner."
  (name      ""    :type string)
  (x         0.0d0 :type double-float)
  (y         0.0d0 :type double-float)
  (z         0.0d0 :type double-float))

(defstruct action
  "A symbolic planner action with preconditions and effects."
  (name         ""  :type string)
  (preconditions nil :type list)
  (effects       nil :type list)
  (cost          1.0 :type single-float))

(defstruct plan-node
  "A search node in the planner's state space."
  (state       nil :type list)
  (action      nil)
  (parent      nil)
  (g-cost      0.0 :type single-float)
  (h-cost      0.0 :type single-float))

(defstruct planner
  "Symbolic planner instance holding the world model and action library."
  (name    "" :type string)
  (drones  nil :type list)
  (actions nil :type list)
  (goals   nil :type list)
  (plan    nil :type list))

;;; ---- World model helpers ----

(defun make-world (num-drones)
  "Create an initial world state with NUM-DRONES idle drones."
  (loop for i from 1 to num-drones
        collect (make-drone-state :id i
                                  :x (* i 10.0d0)
                                  :y 0.0d0
                                  :z 0.0d0
                                  :battery 100.0
                                  :status :idle)))

(defun find-drone (drones id)
  "Return the drone with ID from DRONES list, or NIL."
  (find id drones :key #'drone-state-id))

(defun drone-idle-p (drone)
  "Return T if DRONE is in :idle status."
  (eq (drone-state-status drone) :idle))

(defun drone-low-battery-p (drone &optional (threshold 20.0))
  "Return T if DRONE battery is below THRESHOLD percent."
  (< (drone-state-battery drone) threshold))

;;; ---- Action library ----

(defun make-launch-action ()
  (make-action
    :name "launch"
    :preconditions (list :drone-idle :battery-ok)
    :effects (list :drone-airborne)
    :cost 2.0))

(defun make-navigate-action ()
  (make-action
    :name "navigate"
    :preconditions (list :drone-airborne :waypoint-reachable)
    :effects (list :drone-at-waypoint)
    :cost 5.0))

(defun make-land-action ()
  (make-action
    :name "land"
    :preconditions (list :drone-airborne)
    :effects (list :drone-idle :drone-landed)
    :cost 2.0))

(defun make-return-to-home-action ()
  (make-action
    :name "return-to-home"
    :preconditions (list :drone-airborne)
    :effects (list :drone-at-home :drone-idle)
    :cost 8.0))

;;; ---- Planner logic ----

(defun check-preconditions (action state)
  "Return T if all preconditions of ACTION are satisfied in STATE."
  (every (lambda (pre) (member pre state)) (action-preconditions action)))

(defun apply-effects (action state)
  "Return new state after applying ACTION effects."
  (let ((new-state (copy-list state)))
    (dolist (eff (action-effects action) new-state)
      (pushnew eff new-state))))

(defun goal-satisfied-p (goals state)
  "Return T if all GOALS are present in STATE."
  (every (lambda (g) (member g state)) goals))

(defun plan-mission (planner initial-state)
  "Run a simple forward-chaining symbolic planner from INITIAL-STATE."
  (format t "~%[Planner: ~a] Starting forward-chaining plan~%" (planner-name planner))
  (let ((current-state initial-state)
        (plan-steps '()))
    (loop for action in (planner-actions planner) do
      (when (check-preconditions action current-state)
        (setf current-state (apply-effects action current-state))
        (push (action-name action) plan-steps)
        (format t "  Applied: ~a~%  State: ~a~%" (action-name action) current-state)
        (when (goal-satisfied-p (planner-goals planner) current-state)
          (format t "[Planner] Goal reached!~%")
          (return (reverse plan-steps)))))
    (format t "[Planner] Plan: ~a~%" (reverse plan-steps))
    (setf (planner-plan planner) (reverse plan-steps))
    (planner-plan planner)))

;;; ---- Main entry point ----

(defun run-sdacs-planner ()
  (let* ((world (make-world 3))
         (p (make-planner
              :name "SDACS-Symbolic"
              :drones world
              :actions (list (make-launch-action)
                             (make-navigate-action)
                             (make-land-action))
              :goals (list :drone-at-waypoint :drone-idle))))
    (format t "Drones: ~a~%" (length (planner-drones p)))
    (plan-mission p (list :drone-idle :battery-ok :waypoint-reachable))))

(run-sdacs-planner)
