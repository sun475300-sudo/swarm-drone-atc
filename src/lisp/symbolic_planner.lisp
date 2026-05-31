;;; P599: SymbolicPlanner - Common Lisp symbolic AI planner for drone missions
;;; Phase 599: STRIPS-based mission planning for autonomous drone operations

(defpackage :sdacs.planner
  (:use :cl)
  (:export :make-state :make-action :plan :apply-action :goal-satisfied-p))

(in-package :sdacs.planner)

;;; State representation
(defstruct (state (:constructor make-state (&key facts)))
  (facts '() :type list))

(defstruct (action (:constructor make-action (&key name preconditions add-effects del-effects cost)))
  (name         ""  :type string)
  (preconditions '() :type list)
  (add-effects   '() :type list)
  (del-effects   '() :type list)
  (cost          1.0 :type float))

;;; Check if a fact holds in a state
(defun fact-holds-p (fact state)
  (member fact (state-facts state) :test #'equal))

;;; Check if all preconditions are met
(defun preconditions-met-p (action state)
  (every (lambda (prec) (fact-holds-p prec state))
         (action-preconditions action)))

;;; Apply an action to produce a new state
(defun apply-action (action state)
  (when (preconditions-met-p action state)
    (let ((new-facts (set-difference (state-facts state)
                                     (action-del-effects action)
                                     :test #'equal)))
      (make-state :facts (union new-facts
                                (action-add-effects action)
                                :test #'equal)))))

;;; Check if a goal (list of facts) is satisfied
(defun goal-satisfied-p (goal state)
  (every (lambda (g) (fact-holds-p g state)) goal))

;;; BFS planner: find a plan (sequence of actions) to reach goal
(defun plan (initial-state goal actions &key (max-depth 10))
  (let ((queue (list (list initial-state '())))
        (visited '()))
    (loop while queue
          for (current-state path) = (pop queue)
          do
          (when (goal-satisfied-p goal current-state)
            (return (reverse path)))
          (unless (member (state-facts current-state) visited :test #'equal)
            (push (state-facts current-state) visited)
            (when (< (length path) max-depth)
              (dolist (action actions)
                (let ((new-state (apply-action action current-state)))
                  (when new-state
                    (setf queue (append queue
                                        (list (list new-state
                                                    (cons action path))))))))))
          finally (return nil))))

;;; Domain-specific drone actions
(defparameter *drone-actions*
  (list
   (make-action :name "takeoff"
                :preconditions '((grounded) (battery-ok))
                :add-effects   '((airborne) (at-cruise-altitude))
                :del-effects   '((grounded))
                :cost          2.0)
   (make-action :name "fly-to-target"
                :preconditions '((airborne) (battery-ok) (at-cruise-altitude))
                :add-effects   '((at-target))
                :del-effects   '()
                :cost          5.0)
   (make-action :name "land"
                :preconditions '((airborne))
                :add-effects   '((grounded))
                :del-effects   '((airborne) (at-cruise-altitude) (at-target))
                :cost          2.0)
   (make-action :name "recharge"
                :preconditions '((grounded))
                :add-effects   '((battery-ok))
                :del-effects   '()
                :cost          10.0)))

;;; Example planning invocation
(defun plan-delivery-mission ()
  (let* ((start  (make-state :facts '((grounded) (battery-ok))))
         (goal   '((at-target) (airborne)))
         (result (plan start goal *drone-actions*)))
    (if result
        (format t "Plan found: ~{~A~^, ~}~%" (mapcar #'action-name result))
        (format t "No plan found~%"))
    result))
